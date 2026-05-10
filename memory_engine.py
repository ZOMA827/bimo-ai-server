# memory_engine.py — ذاكرة بيمو الحقيقية

import json
import os
import time

MEMORY_FILE = "memory.json"

DEFAULT_MEMORY = {
    "user_name": "",
    "notes": "",
    "favorite_game": "",
    "favorite_anime": "",
    "favorite_music": "",
    "mood_history": [],       # آخر 5 مزاجيات
    "last_topic": "",
    "last_seen": "",
    "relationship_level": 1,  # 1=جديد → 10=صديق حقيقي
}


class MemoryEngine:
    def __init__(self):
        self.memory = self._load()

    def _load(self) -> dict:
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # دمج مع الافتراضي لضمان وجود كل المفاتيح
                    merged = {**DEFAULT_MEMORY, **loaded}
                    return merged
            except Exception:
                pass
        return DEFAULT_MEMORY.copy()

    def save_memory(self, new_data: dict):
        """يدمج البيانات الجديدة مع الموجودة ويحفظ"""
        if not new_data:
            return

        # لا تمسح الذاكرة القديمة — ادمجها
        for key, value in new_data.items():
            if value:  # لا تحفظ قيماً فارغة
                self.memory[key] = value

        # تحديث وقت آخر تحدث
        self.memory["last_seen"] = time.strftime("%Y-%m-%d %H:%M")

        # ارفع مستوى العلاقة تدريجياً
        if self.memory.get("relationship_level", 1) < 10:
            self.memory["relationship_level"] = min(
                10,
                self.memory.get("relationship_level", 1) + 0.1
            )

        try:
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Memory save error: {e}")

    def add_mood(self, mood: str):
        """يضيف مزاج للتاريخ (آخر 5 فقط)"""
        history = self.memory.get("mood_history", [])
        history.append({"mood": mood, "time": time.strftime("%H:%M")})
        self.memory["mood_history"] = history[-5:]
        self.save_memory({})

    def get_memory(self) -> dict:
        return self.memory

    def reset(self):
        """إعادة ضبط كاملة — تُستخدم فقط عند الطلب الصريح"""
        self.memory = DEFAULT_MEMORY.copy()
        if os.path.exists(MEMORY_FILE):
            os.remove(MEMORY_FILE)