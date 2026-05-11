# memory_engine.py — ذاكرة بيمو السحابية الخالدة (Firebase Edition) ☁️
# ✅ حقول جديدة لكل الاهتمامات + حماية ضد مسح البيانات واختراع المفاتيح

import firebase_admin
from firebase_admin import credentials, db
import os, json, time

DEFAULT_MEMORY = {
    "user_name":        "",
    "notes":            "",
    "hobby":            "",         # ← جديد: هوايات عامة
    "favorite_game":    "",
    "favorite_anime":   "",
    "favorite_music":   "",
    "favorite_show":    "",         # ← جديد: مسلسلات / أفلام
    "favorite_sport":   "",         # ← جديد: رياضة
    "mood_history":     [],
    "last_topic":       "",
    "last_seen":        "",
    "preferred_lang":   "arabic",   # ← جديد: اللغة المفضلة
    "relationship_level": 1,
}

class MemoryEngine:
    def __init__(self):
        if not firebase_admin._apps:
            try:
                config_raw = os.environ.get("FIREBASE_CONFIG")
                db_url     = os.environ.get("FIREBASE_DB_URL")
                if config_raw and db_url:
                    cred = credentials.Certificate(json.loads(config_raw))
                    firebase_admin.initialize_app(cred, {'databaseURL': db_url})
                    print("✅ Firebase متصل")
                else:
                    print("⚠️ إعدادات Firebase غير موجودة")
            except Exception as e:
                print(f"❌ Firebase فشل: {e}")

        self.db_ref = db.reference("bimo_memory")
        self.memory = self._load()

    def _load(self) -> dict:
        try:
            data = self.db_ref.get()
            if data:
                return {**DEFAULT_MEMORY, **data}
        except Exception as e:
            print(f"⚠️ خطأ في جلب الذاكرة: {e}")
        return DEFAULT_MEMORY.copy()

    def get(self) -> dict:
        return self.memory

    def save(self, new_data: dict):
        if not new_data:
            return
            
        for key, value in new_data.items():
            if not value:  # تجاهل القيم الفارغة (حتى لا يمسح اسمك إذا أرسل قيمة فارغة)
                continue
                
            # 1. فلتر الذكاء الاصطناعي (منع اختراع مفاتيح وهمية مثل friend_name)
            if key not in DEFAULT_MEMORY:
                # إذا اخترع مفتاح "name" بالخطأ، نوجهه للمفتاح الصحيح "user_name"
                if key == "name":
                    self.memory["user_name"] = str(value)
                else:
                    # أي اختراع آخر نضعه كـ "ملاحظة" لكي لا نلوث قاعدة البيانات
                    old_notes = self.memory.get("notes", "")
                    addition = f"{key}: {value}"
                    if addition not in old_notes:
                        self.memory["notes"] = f"{old_notes} | {addition}".strip(" |")
                continue

            # 2. ميزة التراكم (Append) للملاحظات حتى لا يمسح الماضي!
            if key == "notes" or key == "hobby":
                old_val = self.memory.get(key, "")
                if str(value) not in old_val:
                    self.memory[key] = f"{old_val} | {value}".strip(" |")
            else:
                # تحديث طبيعي لباقي القيم (مثل user_name)
                self.memory[key] = str(value)

        self.memory["last_seen"] = time.strftime("%Y-%m-%d %H:%M")

        # ─── رفع مستوى العلاقة ───
        lvl = self.memory.get("relationship_level", 1)
        if lvl < 10:
            self.memory["relationship_level"] = round(min(10, lvl + 0.1), 2)

        # ─── كشف اللغة المفضلة ───
        topic = new_data.get("last_topic", "")
        if topic:
            arabic_chars = sum(1 for c in topic if '\u0600' <= c <= '\u06FF')
            latin_chars  = sum(1 for c in topic if c.isalpha() and c.isascii())
            if arabic_chars > latin_chars:
                self.memory["preferred_lang"] = "arabic"
            elif latin_chars > arabic_chars:
                self.memory["preferred_lang"] = "latin"

        try:
            self.db_ref.set(self.memory)
            print(f"☁️ الذاكرة محفوظة ومحمية: {list(new_data.keys())}")
        except Exception as e:
            print(f"❌ فشل الحفظ: {e}")

    def add_mood(self, mood: str):
        history = self.memory.get("mood_history", [])
        history.append({"mood": mood, "time": time.strftime("%H:%M")})
        self.memory["mood_history"] = history[-5:]
        self.save({})

    def reset(self):
        self.memory = DEFAULT_MEMORY.copy()
        try:
            self.db_ref.set(self.memory)
            print("🧹 الذاكرة صُفِّرت")
        except Exception as e:
            print(f"❌ فشل التصفير: {e}")