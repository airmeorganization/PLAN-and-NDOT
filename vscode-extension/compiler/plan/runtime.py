"""PLAN Runtime Helper Module (plan_rt).

This module is imported by generated Python code to provide runtime helpers
for 1-based indexing, numeric conversion, and friendly English errors.
"""
import sys

def to_number(val, line=None):
    """Converts a value to int if integral, otherwise float."""
    if isinstance(val, (int, float)):
        return val
    try:
        s = str(val).strip()
        if '.' in s:
            f = float(s)
            return int(f) if f.is_integer() else f
        return int(s)
    except ValueError:
        prefix = f"Line {line}: " if line else ""
        raise ValueError(f"{prefix}Cannot convert '{val}' to a number.")

def to_whole_number(val, line=None):
    """Converts a value to int."""
    if isinstance(val, int):
        return val
    try:
        return int(float(str(val).strip()))
    except ValueError:
        prefix = f"Line {line}: " if line else ""
        raise ValueError(f"{prefix}Cannot convert '{val}' to a whole number.")

def item(seq, n, line=None):
    """1-based indexing for PLAN collections with English error messages."""
    try:
        idx = int(n)
        if idx <= 0:
            prefix = f"Line {line}: " if line else ""
            raise IndexError(f"{prefix}PLAN indexing is 1-based, but received index {idx}.")
        return seq[idx - 1]
    except IndexError:
        prefix = f"Line {line}: " if line else ""
        length = len(seq) if hasattr(seq, '__len__') else 'unknown'
        raise IndexError(f"{prefix}there is no item {n} in sequence — it only has {length} items.")

def set_item(seq, n, val, line=None):
    """1-based index assignment."""
    try:
        idx = int(n)
        if idx <= 0:
            prefix = f"Line {line}: " if line else ""
            raise IndexError(f"{prefix}PLAN indexing is 1-based, but received index {idx}.")
        seq[idx - 1] = val
    except IndexError:
        prefix = f"Line {line}: " if line else ""
        length = len(seq) if hasattr(seq, '__len__') else 'unknown'
        raise IndexError(f"{prefix}cannot set item {n} — sequence only has {length} items.")

def entry(mapping, key, line=None):
    """Access dictionary entry."""
    try:
        return mapping[key]
    except KeyError:
        prefix = f"Line {line}: " if line else ""
        raise KeyError(f"{prefix}entry '{key}' not found in dictionary.")

def set_entry(mapping, key, val, line=None):
    """Set dictionary entry."""
    mapping[key] = val
