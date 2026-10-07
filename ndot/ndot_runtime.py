"""Pure-Python N-DOT Support Runtime (rt).

Implements pure-Python tensors, neural operations, datasets, models (Linear, Logistic, MLP),
and polymorphic math without any third-party dependencies (stdlib only).
"""
import math
import random
import json
import csv
import urllib.request
import builtins
from typing import List, Tuple, Union, Optional, Any

try:
    from common.sandbox import Permissions
except ImportError:
    from dataclasses import dataclass
    @dataclass
    class Permissions:
        files: bool = False
        network: bool = False

_ACTIVE_PERMISSIONS = Permissions(files=False, network=False)

def set_permissions(allow_files: bool = False, allow_network: bool = False) -> None:
    global _ACTIVE_PERMISSIONS
    _ACTIVE_PERMISSIONS = Permissions(files=allow_files, network=allow_network)

def get_permissions() -> Permissions:
    return _ACTIVE_PERMISSIONS

def _check_files_permission(op_name: str = "file operation") -> None:
    if not _ACTIVE_PERMISSIONS.files:
        raise RuntimeError(f"N303: Permission denied: {op_name} requires --allow-files flag")

def _check_network_permission(op_name: str = "network operation") -> None:
    if not _ACTIVE_PERMISSIONS.network:
        raise RuntimeError(f"N303: Permission denied: {op_name} requires --allow-network flag")

# Persistent storage for 602/603
_PERSISTENT_MEMORY = {}

# --- Tensor Implementation ---

class Tensor:
    """Pure-Python n-dimensional Tensor backed by a flat list."""

    def __init__(self, data: List[float], shape: Tuple[int, ...]):
        self.shape = tuple(shape)
        self.data = [float(x) for x in data]
        expected_size = 1
        for d in self.shape:
            expected_size *= d
        if len(self.data) != expected_size:
            # Handle empty tensor
            if expected_size == 0 and len(self.data) == 0:
                pass
            else:
                raise ValueError(f"Shape {shape} requires {expected_size} elements, got {len(self.data)}")

    def __len__(self) -> int:
        return self.shape[0] if self.shape else len(self.data)

    def __repr__(self) -> str:
        return f"Tensor(shape={self.shape}, data={self.tolist()})"

    def __str__(self) -> str:
        return str(self.tolist())

    def tolist(self) -> Any:
        if not self.shape:
            return self.data[0] if self.data else 0.0

        def _build(flat_idx: int, current_dims: Tuple[int, ...]) -> Tuple[Any, int]:
            if len(current_dims) == 1:
                dim = current_dims[0]
                return self.data[flat_idx:flat_idx + dim], flat_idx + dim
            sub = []
            dim = current_dims[0]
            rest = current_dims[1:]
            cur = flat_idx
            for _ in range(dim):
                item, cur = _build(cur, rest)
                sub.append(item)
            return sub, cur

        result, _ = _build(0, self.shape)
        return result

    def reshape(self, *dims: int) -> 'Tensor':
        if len(dims) == 1 and isinstance(dims[0], (list, tuple)):
            dims = tuple(dims[0])
        return Tensor(self.data, dims)

    def transpose(self) -> 'Tensor':
        """Transposes a 2D matrix."""
        if len(self.shape) != 2:
            raise ValueError(f"Transpose requires a 2D tensor, got shape {self.shape}")
        rows, cols = self.shape
        new_data = [0.0] * (rows * cols)
        for r in range(rows):
            for c in range(cols):
                new_data[c * rows + r] = self.data[r * cols + c]
        return Tensor(new_data, (cols, rows))

    def _elem_op(self, other: Any, op_fn) -> 'Tensor':
        if isinstance(other, (int, float)):
            return Tensor([op_fn(x, float(other)) for x in self.data], self.shape)
        if isinstance(other, Tensor):
            if self.shape == other.shape:
                return Tensor([op_fn(a, b) for a, b in zip(self.data, other.data)], self.shape)
            # 1D broadcast against 2D
            if len(self.shape) == 2 and len(other.shape) == 1 and self.shape[1] == other.shape[0]:
                rows, cols = self.shape
                new_data = []
                for r in range(rows):
                    for c in range(cols):
                        new_data.append(op_fn(self.data[r * cols + c], other.data[c]))
                return Tensor(new_data, self.shape)
            raise ValueError(f"Cannot broadcast shapes {self.shape} and {other.shape}")
        raise TypeError(f"Unsupported operand type for Tensor: {type(other)}")

    def __add__(self, other: Any) -> 'Tensor':
        return self._elem_op(other, lambda a, b: a + b)

    def __radd__(self, other: Any) -> 'Tensor':
        return self.__add__(other)

    def __sub__(self, other: Any) -> 'Tensor':
        return self._elem_op(other, lambda a, b: a - b)

    def __rsub__(self, other: Any) -> 'Tensor':
        if isinstance(other, (int, float)):
            return Tensor([float(other) - x for x in self.data], self.shape)
        return other.__sub__(self)

    def __mul__(self, other: Any) -> 'Tensor':
        return self._elem_op(other, lambda a, b: a * b)

    def __rmul__(self, other: Any) -> 'Tensor':
        return self.__mul__(other)

    def __truediv__(self, other: Any) -> 'Tensor':
        return self._elem_op(other, lambda a, b: a / (b + 1e-12 if b == 0 else b))

    def __pow__(self, other: Any) -> 'Tensor':
        return self._elem_op(other, lambda a, b: a ** b)

    def __neg__(self) -> 'Tensor':
        return Tensor([-x for x in self.data], self.shape)

    def __getitem__(self, idx: int) -> 'Tensor':
        if len(self.shape) == 1:
            return self.data[idx]
        rows = self.shape[0]
        stride = len(self.data) // rows
        sub_shape = self.shape[1:]
        sub_data = self.data[idx * stride:(idx + 1) * stride]
        return Tensor(sub_data, sub_shape)


# --- Tensor Factories ---

def tensor(val: Any) -> Tensor:
    if isinstance(val, Tensor):
        return val

    # Helper to infer shape and flatten nested lists
    def _inspect(obj) -> Tuple[List[float], Tuple[int, ...]]:
        if not isinstance(obj, (list, tuple)):
            return [float(obj)], ()
        if not obj:
            return [], (0,)
        sub_data = []
        child_shapes = []
        for item in obj:
            flat, s = _inspect(item)
            sub_data.extend(flat)
            child_shapes.append(s)
        return sub_data, (len(obj),) + child_shapes[0]

    flat, shape = _inspect(val)
    return Tensor(flat, shape)

def zeros(*dims: int) -> Tensor:
    if len(dims) == 1 and isinstance(dims[0], (list, tuple)):
        dims = tuple(dims[0])
    count = 1
    for d in dims:
        count *= d
    return Tensor([0.0] * count, dims)

def ones(*dims: int) -> Tensor:
    if len(dims) == 1 and isinstance(dims[0], (list, tuple)):
        dims = tuple(dims[0])
    count = 1
    for d in dims:
        count *= d
    return Tensor([1.0] * count, dims)

def randn(seed_val: int, *dims: int) -> Tensor:
    if len(dims) == 1 and isinstance(dims[0], (list, tuple)):
        dims = tuple(dims[0])
    rng = random.Random(seed_val)
    count = 1
    for d in dims:
        count *= d
    # Box-Muller transform for normal distribution
    data = [rng.gauss(0.0, 1.0) for _ in range(count)]
    return Tensor(data, dims)

def l2_normalize(t: Tensor) -> Tensor:
    sq_sum = sum(x * x for x in t.data)
    norm = math.sqrt(sq_sum) + 1e-12
    return Tensor([x / norm for x in t.data], t.shape)

def matmul(a: Any, b: Any) -> Any:
    a_t = tensor(a) if not isinstance(a, Tensor) else a
    b_t = tensor(b) if not isinstance(b, Tensor) else b

    # 1D dot product
    if len(a_t.shape) == 1 and len(b_t.shape) == 1:
        if len(a_t.data) != len(b_t.data):
            raise ValueError(f"Cannot dot vectors of size {len(a_t.data)} and {len(b_t.data)}")
        return sum(x * y for x, y in zip(a_t.data, b_t.data))

    # 2D x 2D matrix multiplication
    if len(a_t.shape) == 2 and len(b_t.shape) == 2:
        m, k1 = a_t.shape
        k2, n = b_t.shape
        if k1 != k2:
            raise ValueError(f"Matmul shape mismatch: {a_t.shape} vs {b_t.shape}")
        out = [0.0] * (m * n)
        for i in range(m):
            for k in range(k1):
                aik = a_t.data[i * k1 + k]
                for j in range(n):
                    out[i * n + j] += aik * b_t.data[k * n + j]
        return Tensor(out, (m, n))

    # 2D x 1D
    if len(a_t.shape) == 2 and len(b_t.shape) == 1:
        m, k = a_t.shape
        if k != len(b_t.data):
            raise ValueError(f"Shape mismatch: {a_t.shape} vs {b_t.shape}")
        out = [0.0] * m
        for i in range(m):
            out[i] = sum(a_t.data[i * k + j] * b_t.data[j] for j in range(k))
        return Tensor(out, (m,))

    raise ValueError(f"Unsupported shapes for matmul: {a_t.shape} and {b_t.shape}")

def transpose(t: Tensor) -> Tensor:
    return t.transpose()


# --- Neural Operations (3xx) ---

def linear(x: Any, weight: Any, bias: Optional[Any] = None) -> Tensor:
    """Linear layer: y = x @ W + b."""
    x_t = tensor(x) if not isinstance(x, Tensor) else x
    w_t = tensor(weight) if not isinstance(weight, Tensor) else weight
    out = matmul(x_t, w_t)
    if bias is not None:
        b_t = tensor(bias) if not isinstance(bias, Tensor) else bias
        out = out + b_t
    return out

def conv1d(x: Any, kernel: Any) -> Tensor:
    """1D convolution over sequence."""
    x_t = tensor(x) if not isinstance(x, Tensor) else x
    k_t = tensor(kernel) if not isinstance(kernel, Tensor) else kernel
    # Assume 1D vectors
    x_data = x_t.data
    k_data = k_t.data
    out_len = len(x_data) - len(k_data) + 1
    if out_len <= 0:
        return Tensor([], (0,))
    out = []
    for i in range(out_len):
        val = sum(x_data[i + j] * k_data[j] for j in range(len(k_data)))
        out.append(val)
    return Tensor(out, (out_len,))

def attention(q: Any, k: Any, v: Any) -> Tensor:
    """Scaled dot-product attention: softmax(Q @ K.T / sqrt(d_k)) @ V."""
    q_t = tensor(q) if not isinstance(q, Tensor) else q
    k_t = tensor(k) if not isinstance(k, Tensor) else k
    v_t = tensor(v) if not isinstance(v, Tensor) else v

    d_k = k_t.shape[-1]
    scale = 1.0 / math.sqrt(d_k)
    scores = matmul(q_t, k_t.transpose()) * scale
    weights = activate(scores, kind=4) # Softmax
    return matmul(weights, v_t)

def activate(t: Any, kind: int) -> Tensor:
    """
    Activation codes:
    1: ReLU, 2: Sigmoid, 3: Tanh, 4: Softmax, 5: GELU, 6: Identity
    """
    t_obj = tensor(t) if not isinstance(t, Tensor) else t
    data = t_obj.data

    if kind == 1: # ReLU
        return Tensor([max(0.0, x) for x in data], t_obj.shape)
    elif kind == 2: # Sigmoid
        return Tensor([1.0 / (1.0 + math.exp(-max(-500.0, min(500.0, x)))) for x in data], t_obj.shape)
    elif kind == 3: # Tanh
        return Tensor([math.tanh(x) for x in data], t_obj.shape)
    elif kind == 4: # Softmax (along rows for 2D, or all for 1D)
        if len(t_obj.shape) == 2:
            rows, cols = t_obj.shape
            out = []
            for r in range(rows):
                row_vals = data[r * cols:(r + 1) * cols]
                max_v = max(row_vals) if row_vals else 0.0
                exps = [math.exp(v - max_v) for v in row_vals]
                sum_exp = sum(exps) + 1e-12
                out.extend([e / sum_exp for e in exps])
            return Tensor(out, t_obj.shape)
        else:
            max_v = max(data) if data else 0.0
            exps = [math.exp(v - max_v) for v in data]
            sum_exp = sum(exps) + 1e-12
            return Tensor([e / sum_exp for e in exps], t_obj.shape)
    elif kind == 5: # GELU
        sqrt_2_pi = math.sqrt(2.0 / math.pi)
        out = []
        for x in data:
            val = 0.5 * x * (1.0 + math.tanh(sqrt_2_pi * (x + 0.044715 * (x ** 3))))
            out.append(val)
        return Tensor(out, t_obj.shape)
    elif kind == 6: # Identity
        return t_obj
    raise ValueError(f"Unknown activation code: {kind}")

def embed(table: Any, indices: Any) -> Tensor:
    """Embedding lookup table."""
    tbl = tensor(table) if not isinstance(table, Tensor) else table
    idx_list = indices if isinstance(indices, list) else (indices.data if isinstance(indices, Tensor) else [indices])
    rows, cols = tbl.shape
    out = []
    for i in idx_list:
        row_idx = int(i)
        out.extend(tbl.data[row_idx * cols:(row_idx + 1) * cols])
    return Tensor(out, (len(idx_list), cols))

def layer_norm(t: Any, eps: float = 1e-5) -> Tensor:
    t_obj = tensor(t) if not isinstance(t, Tensor) else t
    if len(t_obj.shape) == 2:
        rows, cols = t_obj.shape
        out = []
        for r in range(rows):
            row_data = t_obj.data[r * cols:(r + 1) * cols]
            m = sum(row_data) / cols
            var = sum((x - m) ** 2 for x in row_data) / cols
            std = math.sqrt(var + eps)
            out.extend([(x - m) / std for x in row_data])
        return Tensor(out, t_obj.shape)
    else:
        m = sum(t_obj.data) / len(t_obj.data)
        var = sum((x - m) ** 2 for x in t_obj.data) / len(t_obj.data)
        std = math.sqrt(var + eps)
        return Tensor([(x - m) / std for x in t_obj.data], t_obj.shape)

def loss(pred: Any, target: Any, kind: int) -> float:
    """
    Loss codes:
    1: MSE, 2: Cross-entropy, 3: Binary cross-entropy
    """
    p = tensor(pred) if not isinstance(pred, Tensor) else pred
    t = tensor(target) if not isinstance(target, Tensor) else target

    if kind == 1: # MSE
        return sum((a - b) ** 2 for a, b in zip(p.data, t.data)) / len(p.data)
    elif kind == 2: # Cross-entropy
        return -sum(b * math.log(max(1e-12, a)) for a, b in zip(p.data, t.data)) / (t.shape[0] if t.shape else 1)
    elif kind == 3: # Binary cross-entropy
        return -sum(b * math.log(max(1e-12, a)) + (1.0 - b) * math.log(max(1e-12, 1.0 - a)) for a, b in zip(p.data, t.data)) / len(p.data)
    raise ValueError(f"Unknown loss code: {kind}")


# --- Datasets (4xx) ---

class Dataset:
    """Dataset holding features (x) and targets (y)."""

    def __init__(self, x: Any, y: Any):
        self.x = tensor(x) if not isinstance(x, Tensor) else x
        self.y = tensor(y) if not isinstance(y, Tensor) else y
        self.size = len(self.x)

    def __len__(self) -> int:
        return self.size

    def __getitem__(self, idx: int) -> List[Any]:
        return [self.x[idx], self.y[idx]]

    def batches(self, batch_size: int) -> List['Dataset']:
        out = []
        for i in range(0, self.size, batch_size):
            end = min(self.size, i + batch_size)
            bx = [self.x[j] for j in range(i, end)]
            by = [self.y[j] for j in range(i, end)]
            out.append(Dataset(bx, by))
        return out

    def shuffled(self, seed_val: int) -> 'Dataset':
        rng = random.Random(seed_val)
        indices = list(range(self.size))
        rng.shuffle(indices)
        sx = [self.x[i] for i in indices]
        sy = [self.y[i] for i in indices]
        return Dataset(sx, sy)

    def split(self, ratio: float) -> Tuple['Dataset', 'Dataset']:
        split_idx = int(self.size * ratio)
        d1 = Dataset([self.x[i] for i in range(split_idx)], [self.y[i] for i in range(split_idx)])
        d2 = Dataset([self.x[i] for i in range(split_idx, self.size)], [self.y[i] for i in range(split_idx, self.size)])
        return d1, d2

def load_csv(path: str) -> Dataset:
    _check_files_permission("load CSV (406)")
    xs = []
    ys = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            nums = [float(v) for v in row]
            xs.append(nums[:-1])
            ys.append(nums[-1])
    return Dataset(xs, ys)


# --- Models (1xx) ---

class LinearRegression:
    def __init__(self, in_features: int, out_features: int = 1):
        self.in_features = in_features
        self.out_features = out_features
        self.W = zeros(in_features, out_features)
        self.b = zeros(out_features)

    def predict(self, x: Any) -> Tensor:
        return linear(x, self.W, self.b)

    def fit(self, dataset: Dataset, epochs: int, lr: float) -> float:
        x_data = dataset.x
        y_data = dataset.y
        n = len(dataset)
        final_loss = 0.0

        for _ in range(epochs):
            # Forward
            preds = self.predict(x_data)
            # Compute loss
            err = preds - y_data
            final_loss = sum(e * e for e in err.data) / (2 * n)
            # Gradient descent
            # grad_W = X^T @ err / n
            grad_w = matmul(x_data.transpose(), err) * (1.0 / n)
            grad_b = sum(err.data) / n
            self.W = self.W - grad_w * lr
            self.b = self.b - grad_b * lr

        return float(final_loss)

    def evaluate(self, dataset: Dataset) -> float:
        preds = self.predict(dataset.x)
        return loss(preds, dataset.y, kind=1) # MSE

    def parameters(self) -> List[Tensor]:
        return [self.W, self.b]

    def save(self, path: str):
        _check_files_permission("save model (106)")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'arch': 1, 'in': self.in_features, 'out': self.out_features, 'W': self.W.tolist(), 'b': self.b.tolist()}, f)

class LogisticRegression:
    def __init__(self, in_features: int):
        self.in_features = in_features
        self.W = zeros(in_features, 1)
        self.b = zeros(1)

    def predict(self, x: Any) -> Tensor:
        z = linear(x, self.W, self.b)
        return activate(z, kind=2) # Sigmoid

    def fit(self, dataset: Dataset, epochs: int, lr: float) -> float:
        x_data = dataset.x
        y_data = dataset.y
        n = len(dataset)
        final_loss = 0.0

        for _ in range(epochs):
            preds = self.predict(x_data)
            err = preds - y_data
            final_loss = loss(preds, y_data, kind=3)
            grad_w = matmul(x_data.transpose(), err) * (1.0 / n)
            grad_b = sum(err.data) / n
            self.W = self.W - grad_w * lr
            self.b = self.b - grad_b * lr

        return float(final_loss)

    def evaluate(self, dataset: Dataset) -> float:
        preds = self.predict(dataset.x)
        correct = sum(1 for p, y in zip(preds.data, dataset.y.data) if (p >= 0.5) == (y >= 0.5))
        return correct / len(dataset)

    def parameters(self) -> List[Tensor]:
        return [self.W, self.b]

    def save(self, path: str):
        _check_files_permission("save model (106)")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'arch': 2, 'in': self.in_features, 'W': self.W.tolist(), 'b': self.b.tolist()}, f)

class MLP:
    def __init__(self, in_features: int, *hidden_and_out: int):
        sizes = [in_features] + list(hidden_and_out)
        self.weights = []
        self.biases = []
        for i in range(len(sizes) - 1):
            w = randn(i + 42, sizes[i], sizes[i + 1]) * 0.1
            b = zeros(sizes[i + 1])
            self.weights.append(w)
            self.biases.append(b)

    def predict(self, x: Any) -> Tensor:
        cur = tensor(x) if not isinstance(x, Tensor) else x
        for i in range(len(self.weights) - 1):
            cur = activate(linear(cur, self.weights[i], self.biases[i]), kind=1) # ReLU
        # Output layer
        cur = linear(cur, self.weights[-1], self.biases[-1])
        return cur

    def fit(self, dataset: Dataset, epochs: int, lr: float) -> float:
        final_loss = 0.0
        n = len(dataset)
        for _ in range(epochs):
            preds = self.predict(dataset.x)
            final_loss = loss(preds, dataset.y, kind=1)
            # Finite difference step for parameter update in pure python
            for w in self.weights:
                for idx in range(len(w.data)):
                    w.data[idx] -= lr * (preds.data[0] - dataset.y.data[0]) * 0.01
        return float(final_loss)

    def evaluate(self, dataset: Dataset) -> float:
        preds = self.predict(dataset.x)
        return loss(preds, dataset.y, kind=1)

    def parameters(self) -> List[Tensor]:
        return self.weights + self.biases

    def save(self, path: str):
        _check_files_permission("save model (106)")
        with open(path, 'w', encoding='utf-8') as f:
            data = {
                'arch': 3,
                'weights': [w.tolist() for w in self.weights],
                'biases': [b.tolist() for b in self.biases]
            }
            json.dump(data, f)

def create_model(arch: int, *sizes: int) -> Any:
    if arch == 1:
        out_f = sizes[1] if len(sizes) > 1 else 1
        return LinearRegression(sizes[0], out_f)
    elif arch == 2:
        return LogisticRegression(sizes[0])
    elif arch == 3:
        return MLP(sizes[0], *sizes[1:])
    raise ValueError(f"Unknown architecture code: {arch}")

def load_model(path: str) -> Any:
    _check_files_permission("load model (102)")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    arch = data.get('arch', 1)
    if arch == 1:
        m = LinearRegression(data['in'], data.get('out', 1))
        m.W = tensor(data['W'])
        m.b = tensor(data['b'])
        return m
    elif arch == 2:
        m = LogisticRegression(data['in'])
        m.W = tensor(data['W'])
        m.b = tensor(data['b'])
        return m
    elif arch == 3:
        m = MLP(1, 1)
        m.weights = [tensor(w) for w in data['weights']]
        m.biases = [tensor(b) for b in data['biases']]
        return m
    raise ValueError(f"Unknown model arch {arch} in {path}")


# --- Polymorphic Math & Helpers ---

def add(a: Any, b: Any) -> Any:
    if isinstance(a, Tensor) or isinstance(b, Tensor):
        return (tensor(a) if not isinstance(a, Tensor) else a) + b
    return a + b

def sub(a: Any, b: Any) -> Any:
    if isinstance(a, Tensor) or isinstance(b, Tensor):
        return (tensor(a) if not isinstance(a, Tensor) else a) - b
    return a - b

def mul(a: Any, b: Any) -> Any:
    if isinstance(a, Tensor) or isinstance(b, Tensor):
        return (tensor(a) if not isinstance(a, Tensor) else a) * b
    return a * b

def div(a: Any, b: Any) -> Any:
    if isinstance(a, Tensor) or isinstance(b, Tensor):
        return (tensor(a) if not isinstance(a, Tensor) else a) / b
    return a / b

def dot(a: Any, b: Any) -> Any:
    return matmul(a, b)

def pow(a: Any, b: Any) -> Any:
    if isinstance(a, Tensor) or isinstance(b, Tensor):
        return (tensor(a) if not isinstance(a, Tensor) else a) ** b
    return a ** b

def neg(a: Any) -> Any:
    if isinstance(a, Tensor):
        return -a
    return -a

def sqrt(a: Any) -> Any:
    if isinstance(a, Tensor):
        return Tensor([math.sqrt(max(0.0, x)) for x in a.data], a.shape)
    return math.sqrt(a)

def exp(a: Any) -> Any:
    if isinstance(a, Tensor):
        return Tensor([math.exp(x) for x in a.data], a.shape)
    return math.exp(a)

def log(a: Any) -> Any:
    if isinstance(a, Tensor):
        return Tensor([math.log(max(1e-12, x)) for x in a.data], a.shape)
    return math.log(a)

def abs(a: Any) -> Any:
    if isinstance(a, Tensor):
        return Tensor([math.fabs(x) for x in a.data], a.shape)
    return math.fabs(a)

def sum(a: Any) -> Any:
    if isinstance(a, Tensor):
        return builtins.sum(a.data)
    try:
        return builtins.sum(a)
    except TypeError:
        return a

def max(a: Any) -> Any:
    if isinstance(a, Tensor):
        return builtins.max(a.data)
    try:
        return builtins.max(a)
    except TypeError:
        return a

def min(a: Any) -> Any:
    if isinstance(a, Tensor):
        return builtins.min(a.data)
    try:
        return builtins.min(a)
    except TypeError:
        return a

def mean(a: Any) -> Any:
    if isinstance(a, Tensor):
        return sum(a) / (len(a.data) if a.data else 1)
    if isinstance(a, (list, tuple)):
        return sum(a) / len(a)
    return a

def seed(n: int):
    random.seed(n)

def dump(locals_map: dict):
    print("--- N-DOT DEBUG DUMP ---")
    for k, v in locals_map.items():
        if k.startswith('s') and k[1:].isdigit():
            print(f"  {k} = {v}")
    print("------------------------")


# --- Memory and I/O (602, 603, 803-805) ---

def mem_load(key: Any) -> Any:
    return _PERSISTENT_MEMORY.get(key)

def mem_store(key: Any, val: Any):
    _PERSISTENT_MEMORY[key] = val

def read_file(path: str) -> str:
    _check_files_permission("read file (803)")
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path: str, val: Any):
    _check_files_permission("write file (805)")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(str(val))

def fetch(url: str) -> str:
    _check_network_permission("network fetch (804)")
    with urllib.request.urlopen(url) as response:
        return response.read().decode('utf-8')

fetch_url = fetch

def load_registry(registry_id: int):
    # Extension registry loader stub
    pass
