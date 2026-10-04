"""Diagnostics shared by both compilers.

A :class:`Diagnostic` is a single error or warning produced by any stage of
either toolchain (lexer, parser, validator, semantic analyzer, runtime).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Diagnostic:
    code: str                      # e.g. "P301" or "N202"
    message: str                   # plain-English explanation
    line: int | None = None        # PLAN source line (1-based)
    location: str | None = None    # free-form location (N-DOT: "instruction 7 (char 58)")
    severity: str = "error"        # "error" | "warning"
    source_text: str | None = None  # offending source excerpt, if available

    @property
    def is_error(self) -> bool:
        return self.severity == "error"

    def format(self, filename: str | None = None) -> str:
        where = []
        if filename:
            where.append(filename)
        if self.line is not None:
            where.append(str(self.line))
        prefix = ":".join(where)
        loc = f" at {self.location}" if self.location else ""
        head = f"{prefix + ': ' if prefix else ''}{self.severity} {self.code}{loc}: {self.message}"
        if self.source_text:
            gutter = f"{self.line:>5} | " if self.line is not None else "      | "
            head += f"\n{gutter}{self.source_text.rstrip()}"
        return head

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.format()


class CompileError(Exception):
    """Raised by a compiler stage that cannot continue (carries diagnostics)."""

    def __init__(self, diagnostics: list[Diagnostic] | Diagnostic):
        if isinstance(diagnostics, Diagnostic):
            diagnostics = [diagnostics]
        self.diagnostics: list[Diagnostic] = list(diagnostics)
        super().__init__("\n".join(d.format() for d in self.diagnostics))


@dataclass
class Report:
    """A collection of diagnostics with helpers."""

    items: list[Diagnostic] = field(default_factory=list)

    def add(self, diag: Diagnostic) -> None:
        self.items.append(diag)

    def error(self, code: str, message: str, **kw) -> None:
        self.items.append(Diagnostic(code, message, severity="error", **kw))

    def warning(self, code: str, message: str, **kw) -> None:
        self.items.append(Diagnostic(code, message, severity="warning", **kw))

    @property
    def errors(self) -> list[Diagnostic]:
        return [d for d in self.items if d.is_error]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [d for d in self.items if not d.is_error]

    @property
    def ok(self) -> bool:
        return not self.errors
