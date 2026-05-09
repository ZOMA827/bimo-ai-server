import json
import os

MEMORY_FILE = "memory.json"
DEFAULT_MEMORY = {"user_name": "إلياس", "notes": "مطور المشروع والمهندس العبقري."}

class MemoryEngine:
    def __init__(self):
        self.memory = self.load_memory()

    def load_memory(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return DEFAULT_MEMORY
        return DEFAULT_MEMORY

    def save_memory(self, memory_data):
        self.memory = memory_data
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=4)

    def get_memory(self):
        return self.memory