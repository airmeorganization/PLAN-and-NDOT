import sys

def to_number(s):
    """
    Converts a string or value to a number.
    Returns int if it's integral, otherwise float.
    Raises a PLAN-worded error if it fails.
    """
    try:
        val = float(s)
        if val.is_integer():
            return int(val)
        return val
    except ValueError:
        raise ValueError(f"I expected a number, but got '{s}'.")

def item(seq, n, line):
    """
    1-based indexing for PLAN collections.
    """
    if not isinstance(n, int):
        raise TypeError(f"Line {line}: list index must be a whole number, not {type(n).__name__}.")
        
    try:
        return seq[n - 1]
    except IndexError:
        count = len(seq)
        if count == 0:
            raise IndexError(f"Line {line}: this list is empty, so there is no item {n}.")
        raise IndexError(f"Line {line}: there is no item {n} — it only has {count} item{'s' if count != 1 else ''}.")
