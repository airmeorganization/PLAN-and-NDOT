"""Map generated-Python line numbers back to source locations."""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field


@dataclass
class SourceMap:
    """python line (1-based) -> source key (PLAN line or N-DOT instruction index)."""

    lines: dict[int, int] = field(default_factory=dict)

    def add(self, python_line: int, source_key: int) -> None:
        self.lines[python_line] = source_key

    def lookup(self, python_line: int) -> int | None:
        if python_line in self.lines:
            return self.lines[python_line]
        # fall back to the closest earlier mapped line
        earlier = [l for l in self.lines if l <= python_line]
        return self.lines[max(earlier)] if earlier else None


def innermost_frame_line(exc: BaseException, filename: str) -> int | None:
    """Return the line number of the deepest traceback frame inside ``filename``."""
    line = None
    for frame in traceback.extract_tb(exc.__traceback__):
        if frame.filename == filename:
            line = frame.lineno
    return line
