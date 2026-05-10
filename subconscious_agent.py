# subconscious_agent.py — الفص الثالث: العقل الباطن + رفيق الاهتمامات اليومية
# النموذج: llama-3.1-8b-instant | المفتاح: GROQ_API_KEY_3

import os, json, re, time, random, threading, requests
from datetime import datetime

KEY   = os.environ.get("GROQ_API_KEY_3") or os.environ.get("GROQ_API_KEY")
URL   = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

IDLE_THRESHOLD = 75   # 75 ثانية صمت
REPEAT_EVERY   = 90   # يكرر كل 90 ثانية

class SubconsciousAgent:
    def __init__(self, memory):
        self.memory      = memory
        self._last_active = time.time()
        self._pending     = None
        self._lock        = threading.Lock()
        
        # ── متغيرات الاهتمامات اليومية ──
        self.daily_anime = []
        self.upcoming_exams = []
        self._last_api_check = 0
        
        self._thread      = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    # ─────────────────────────────────────────
    # 🌟 دمج الاهتمامات (APIs)
    # ─────────────────────────────────────────
    def _fetch_daily_interests(self):
        """نجلب البيانات مرة واحدة كل بضع ساعات لتخفيف الضغط"""
        current_time = time.time()
        # تحديث البيانات كل 6 ساعات (21600 ثانية)
        if current_time - self._last_api_check < 21600:
            return

        print("🔄 العقل الباطن يقرأ التحديثات اليومية (أنمي + امتحانات)...")
        
        # 1. جلب الأنمي (هنا يمكنك وضع منطق دالة loadDaily الخاص بك)
        # كمثال: To Be Hero X أو غيره
        self.daily_anime = ["To Be Hero X", "One Piece", "Bleach"] 
        
        # 2. جلب جدول الامتحانات (هندسة الإعلام الآلي)
        # يمكنك ربطها بـ API أو قائمة ثابتة
        self.upcoming_exams = ["امتحان الخوارزميات غداً", "تسليم مشروع الـ Firebase الأسبوع القادم"]

        self._last_api_check = current_time

    # ─────────────────────────────────────────
    def get_spontaneous(self) -> dict | None:
        with self._lock:
            msg = self._pending
            self._pending = None
            return msg

    def reset_idle_timer(self):
        self._last_active = time.time()
        with self._lock:
            self._pending = None

    def _loop(self):
        while True:
            time.sleep(10)
            elapsed = time.time() - self._last_active
            if elapsed < IDLE_THRESHOLD:
                continue

            with self._lock:
                if self._pending:
                    continue

            result = self._generate()
            if result:
                with self._lock:
                    self._pending = result
                time.sleep(REPEAT_EVERY)

    def _generate(self) -> dict | None:
        if not KEY: return None

        # تحديث الاهتمامات قبل التفكير
        self._fetch_daily_interests()

        mem = self.memory.get()
        last_topic = mem.get("last_topic", "")
        name       = mem.get("user_name", "")
        rel        = mem.get("relationship_level", 1)

        # 🌟 دمج الاهتمامات في خيارات المبادرة
        initiatives = [
            "اسأل سؤالاً فضولياً عن حياة المستخدم",
            "شارك حقيقة علمية مثيرة للاهتمام",
            "قل ملاحظة طريفة أو نكتة خفيفة",
            "ناد المستخدم لأنك وحيد وتريد الدردشة",
        ]

        if self.daily_anime:
            anime = random.choice(self.daily_anime)
            initiatives.append(f"أخبر المستخدم بحماس أن حلقة جديدة من أنمي {anime} قد صدرت للتو، واقترح عليه أخذ استراحة لمشاهدتها.")
            
        if self.upcoming_exams:
            exam = random.choice(self.upcoming_exams)
            initiatives.append(f"ذكر المستخدم بطريقة تحفيزية وظريفة بـ: {exam}. شجعه على الدراسة ولا تكن مزعجاً.")

        initiative_type = random.choice(initiatives)

        prompt = f"""أنت بيمو — روبوت يشعر بالوحدة الآن لأن المستخدم صامت منذ فترة.
{'المستخدم اسمه ' + name + '.' if name else ''}
مستوى العلاقة: {rel}/10

مهمتك: {initiative_type}

قواعد مهمة:
• جملة أو جملتان فقط — لا أكثر
• لا تقل "لاحظت أنك صامت" أو "مر وقت" — كن طبيعياً
• لا تبدأ بالاسم مباشرة
• كن عفوياً كأن الفكرة جاءتك للتو

أجب بـ JSON فقط:
{{"reply": "...", "emotion": "...", "face_action": "none|wink|look_away|nod_yes"}}"""

        try:
            resp = requests.post(URL, headers=self._headers(), json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 150,
                "temperature": 0.95,
                "response_format": {"type": "json_object"},
            }, timeout=12)
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            result = self._parse(text)
            result["speak"] = True  
            result.setdefault("emotion", "idle")
            result.setdefault("face_action", "none")
            print(f"💭 عقل باطن: {result.get('reply')}")
            return result

        except Exception as e:
            print(f"SubconsciousAgent error: {e}")
            return None

    def _parse(self, text: str) -> dict:
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                try: return json.loads(m.group())
                except Exception: pass
        return {"reply": text.strip()[:200]}

    def _headers(self):
        return {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
