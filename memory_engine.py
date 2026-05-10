# memory_engine.py — الذاكرة المشتركة بين الفصوص الثلاثة

import json, os, time

FILE = "memory.json"

DEFAULT = {
    "user_name":         "",
    "notes":             "",
    "favorite_game":     "",
    "favorite_anime":    "",
    "favorite_music":    "",
    "last_topic":        "",
    "last_seen":         "",
    "mood_history":      [],
    "relationship_level": 1,
}

class MemoryEngine:
    def __init__(self):
        self._data = self._load()
        self._lock = __import__('threading').Lock()

    def _load(self) -> dict:
        if os.path.exists(FILE):
            try:
                with open(FILE, "r", encoding="utf-8") as f:
                    return {**DEFAULT, **json.load(f)}
            except Exception:
                pass
        return DEFAULT.copy()

    def get(self) -> dict:
        with self._lock:
            return dict(self._data)

    def save(self, new_data: dict):
        with self._lock:
            for k, v in new_data.items():
                if v:
                    self._data[k] = v
            self._data["last_seen"] = time.strftime("%Y-%m-%d %H:%M")
            lvl = self._data.get("relationship_level", 1)
            self._data["relationship_level"] = round(min(10, lvl + 0.05), 2)
            try:
                with open(FILE, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Memory save error: {e}")

    def add_mood(self, mood: str):
        with self._lock:
            h = self._data.get("mood_history", [])
            h.append({"mood": mood, "t": time.strftime("%H:%M")})
            self._data["mood_history"] = h[-5:]
        self.save({})

    def reset(self):
        with self._lock:
            self._data = DEFAULT.copy()
            if os.path.exists(FILE):
                os.remove(FILE)