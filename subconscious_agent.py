# subconscious_agent.py — الفص الثالث: العقل الباطن
# النموذج: llama-3.1-8b-instant | المفتاح: GROQ_API_KEY_3
# يعمل في الخلفية بصمت — يبادر فقط لما يمر وقت كافٍ

import os, json, re, time, random, threading, requests

KEY   = os.environ.get("GROQ_API_KEY_3") or os.environ.get("GROQ_API_KEY")
URL   = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

# ثانية صمت قبل أن يبادر العقل الباطن
IDLE_THRESHOLD = 75   # 75 ثانية
REPEAT_EVERY   = 90   # يكرر كل 90 ثانية لو لم يرد أحد

class SubconsciousAgent:
    def __init__(self, memory):
        self.memory      = memory
        self._last_active = time.time()
        self._pending     = None      # الرسالة المُعدّة للنطق
        self._lock        = threading.Lock()
        self._thread      = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    # ─── الهاتف يسأل: هل عندك شيء تقوله؟ ───
    def get_spontaneous(self) -> dict | None:
        with self._lock:
            msg = self._pending
            self._pending = None
            return msg  # None لو ما في شيء

    # ─── أعِد العداد عند أي نشاط ───
    def reset_idle_timer(self):
        self._last_active = time.time()
        with self._lock:
            self._pending = None  # ألغِ أي رسالة معلقة

    # ─── الحلقة الداخلية (تعمل في thread منفصل) ───
    def _loop(self):
        while True:
            time.sleep(10)  # يفحص كل 10 ثوانٍ
            elapsed = time.time() - self._last_active
            if elapsed < IDLE_THRESHOLD:
                continue

            with self._lock:
                if self._pending:
                    continue  # لم يُقرأ الأخير بعد

            result = self._generate()
            if result:
                with self._lock:
                    self._pending = result
                # انتظر قبل المحاولة التالية
                time.sleep(REPEAT_EVERY)

    # ─── توليد رسالة مبادرة ───
    def _generate(self) -> dict | None:
        if not KEY:
            return None

        mem = self.memory.get()
        last_topic = mem.get("last_topic", "")
        name       = mem.get("user_name", "")
        rel        = mem.get("relationship_level", 1)

        # اختر نوع المبادرة عشوائياً
        initiative_type = random.choice([
            "اسأل سؤالاً فضولياً عن حياة المستخدم",
            "شارك حقيقة علمية مثيرة للاهتمام",
            "قل ملاحظة طريفة أو نكتة خفيفة",
            "ناد المستخدم لأنك وحيد وتريد الدردشة",
            f"ارجع لموضوع كنتم تتحدثون عنه: {last_topic}" if last_topic else "افتح موضوعاً جديداً",
        ])

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
            result["speak"] = True  # علامة للهاتف أن ينطق
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