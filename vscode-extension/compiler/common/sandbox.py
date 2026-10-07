"""Sandbox policy shared by PLAN and N-DOT.

PLAN uses the module allow-list and the ``allow_python`` switch.
N-DOT uses the ``files`` / ``network`` permissions (checked by ``ndot_runtime``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Modules that PLAN programs may not import unless --allow-all-modules is given.
BLOCKED_MODULES = frozenset({"os", "subprocess", "socket", "ctypes", "shutil", "multiprocessing"})


@dataclass
class Permissions:
    files: bool = False
    network: bool = False
    allow_python: bool = False          # PLAN "Python:" raw lines
    allow_all_modules: bool = False     # PLAN imports outside the allow-list
    blocked_modules: frozenset = field(default_factory=lambda: BLOCKED_MODULES)

    def module_allowed(self, module: str) -> bool:
        if self.allow_all_modules:
            return True
        return module.split(".")[0] not in self.blocked_modules


DEFAULT = Permissions()
