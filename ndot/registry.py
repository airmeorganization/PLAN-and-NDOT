import json
import os
from typing import Dict, Any

class Registry:
    def __init__(self):
        self.opcodes: Dict[str, Any] = {}
        self.load_core()

    def load_core(self):
        path = os.path.join(os.path.dirname(__file__), 'registry.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self.opcodes = json.load(f)

    def get_opcode(self, opcode_id: str) -> Any:
        return self.opcodes.get(opcode_id)

    def get(self, opcode_id: str) -> Any:
        return self.get_opcode(opcode_id)
