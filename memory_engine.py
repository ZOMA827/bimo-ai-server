# memory_engine.py — ذاكرة بيمو السحابية (Firebase Edition) ☁️

import firebase_admin
from firebase_admin import credentials, db
import os
import json
import time

# الحصول على بيانات الفايربيس من متغيرات البيئة (أمان 100%)
# ملاحظة: سنضع محتوى ملف الـ JSON الذي حملته في متغير اسمه FIREBASE_CONFIG
FIREBASE_CONFIG = os.environ.get("FIREBASE_CONFIG")
DATABASE_URL = os.environ.get("FIREBASE_DB_URL")

DEFAULT_MEMORY = {
    "user_name": "",
    "notes": "",
    "favorite_game": "",
    "favorite_anime": "",
    "favorite_music": "",
    "mood_history": [],
    "last_topic": "",
    "last_seen": "",
    "relationship_level": 1,
}

class MemoryEngine:
    def __init__(self):
        # تهيئة الاتصال بفايربيس مرة واحدة فقط
        if not firebase_admin._apps:
            try:
                cred_dict = json.loads(FIREBASE_CONFIG)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': DATABASE_URL
                })
                print("✅ تم الاتصال بـ Firebase بنجاح!")
            except Exception as e:
                print(f"❌ فشل الاتصال بـ Firebase: {e}")

        # المرجع الأساسي للبيانات في قاعدة البيانات
        self.db_ref = db.reference("bimo_memory")
        self.memory = self._load()

    def _load(self) -> dict:
        """جلب الذاكرة من السحابة"""
        try:
            data = self.db_ref.get()
            if data:
                # دمج البيانات المجلوبة مع الهيكل الافتراضي لضمان عدم وجود أخطاء
                return {**DEFAULT_MEMORY, **data}
        except Exception as e:
            print(f"⚠️ خطأ أثناء جلب الذاكرة: {e}")
        return DEFAULT_MEMORY.copy()

    def save_memory(self, new_data: dict):
        """حفظ وتحديث الذاكرة في السحابة فوراً"""
        if not new_data:
            return

        # تحديث الكائن المحلي أولاً
        for key, value in new_data.items():
            if value:
                self.memory[key] = value

        self.memory["last_seen"] = time.strftime("%Y-%m-%d %H:%M")

        # زيادة مستوى العلاقة
        if self.memory.get("relationship_level", 1) < 10:
            self.memory["relationship_level"] = min(
                10,
                self.memory.get("relationship_level", 1) + 0.1
            )

        # الرفع للسحابة (Firebase)
        try:
            self.db_ref.set(self.memory)
            print("☁️ تمت مزامنة الذاكرة مع السحابة.")
        except Exception as e:
            print(f"❌ فشل الحفظ في السحابة: {e}")

    def add_mood(self, mood: str):
        history = self.memory.get("mood_history", [])
        history.append({"mood": mood, "time": time.strftime("%H:%M")})
        self.memory["mood_history"] = history[-5:]
        self.save_memory({})

    def get_memory(self) -> dict:
        return self.memory

    def reset(self):
        """مسح الذاكرة من السحابة"""
        self.memory = DEFAULT_MEMORY.copy()
        try:
            self.db_ref.set(self.memory)
            print("🧹 تم تصقير الذاكرة السحابية.")
        except Exception as e:
            print(f"❌ فشل مسح الذاكرة: {e}")