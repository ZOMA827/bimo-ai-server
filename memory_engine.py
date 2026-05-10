# memory_engine.py — ذاكرة بيمو السحابية الخالدة (Firebase Edition) ☁️

import firebase_admin
from firebase_admin import credentials, db
import os
import json
import time

# 1. تعريف الهيكل الافتراضي للذاكرة (خارج الكلاس ليكون متاحاً للجميع)
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
        # تجنب تهيئة Firebase أكثر من مرة
        if not firebase_admin._apps:
            try:
                # جلب الإعدادات من متغيرات بيئة Render
                config_raw = os.environ.get("FIREBASE_CONFIG")
                db_url = os.environ.get("FIREBASE_DB_URL")
                
                if config_raw and db_url:
                    cred_dict = json.loads(config_raw)
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred, {
                        'databaseURL': db_url
                    })
                    print("✅ تم الاتصال بـ Firebase بنجاح!")
                else:
                    print("⚠️ تحذير: إعدادات Firebase غير موجودة في Environment Variables")
            except Exception as e:
                print(f"❌ فشل الاتصال بـ Firebase: {e}")

        # المرجع الأساسي في قاعدة البيانات
        self.db_ref = db.reference("bimo_memory")
        self.memory = self._load()

    def _load(self) -> dict:
        """جلب الذاكرة من السحابة عند تشغيل السيرفر"""
        try:
            data = self.db_ref.get()
            if data:
                return {**DEFAULT_MEMORY, **data}
        except Exception as e:
            print(f"⚠️ خطأ أثناء جلب الذاكرة: {e}")
        return DEFAULT_MEMORY.copy()

    # ✅ هذه هي الدالة التي يحتاجها ChatAgent و SubconsciousAgent
    def get(self) -> dict:
        """إرجاع الذاكرة الحالية كقاموس"""
        return self.memory

    def save(self, new_data: dict):
        """تحديث الذاكرة في السحابة"""
        if not new_data:
            return

        # دمج البيانات الجديدة
        for key, value in new_data.items():
            if value:
                self.memory[key] = value

        self.memory["last_seen"] = time.strftime("%Y-%m-%d %H:%M")

        # رفع المستوى تدريجياً
        if self.memory.get("relationship_level", 1) < 10:
            self.memory["relationship_level"] = round(min(10, self.memory.get("relationship_level", 1) + 0.1), 2)

        try:
            self.db_ref.set(self.memory)
            print("☁️ تمت مزامنة الذاكرة مع Firebase.")
        except Exception as e:
            print(f"❌ فشل الحفظ السحابي: {e}")

    def reset(self):
        """مسح الذاكرة وإعادتها للافتراض في السحابة"""
        self.memory = DEFAULT_MEMORY.copy()
        try:
            self.db_ref.set(self.memory)
            print("🧹 تم تصقير الذاكرة السحابية بنجاح.")
        except Exception as e:
            print(f"❌ فشل مسح الذاكرة: {e}")