# chat_agent.py — الفص الأول: وكيل الحوار السريع
# ✅ تم التحديث إلى Llama 3.1 8B Instant لتفادي قيود السيرفر المجانية (Error 429)

import os, json, re, requests

KEY = os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY")
URL = "https://api.groq.com/openai/v1/chat/completions"
# 🔥 التحديث السحري: هذا النموذج السريع يملك حدود استخدام ضخمة ولن يوقفك!
MODEL = "llama-3.1-8b-instant"

class ChatAgent:
    def __init__(self, memory):
        self.memory = memory
        self.history = []
        self.MAX_HISTORY = 6  # ذاكرة خفيفة لحماية السيرفر

    # ─────────────────────────────────────────
    def reply(self, message: str, vision_data: dict = {}) -> dict:
        if not KEY:
            return self._err("مفتاح API مفقود!")

        mem = self.memory.get()
        is_smiling = vision_data.get("is_user_smiling", False)
        suppress_name = vision_data.get("suppress_name", False)

        system = self._build_prompt(mem, is_smiling, suppress_name)

        messages = [{"role": "system", "content": system}]
        for m in self.history[-self.MAX_HISTORY:]:
            messages.append(m)
        messages.append({"role": "user", "content": message})

        try:
            resp = requests.post(URL, headers=self._headers(), json={
                "model": MODEL,
                "messages": messages,
                "max_tokens": 1024, # مساحة ممتازة للقصص الطويلة
                "temperature": self._temperature(mem),
                "response_format": {"type": "json_object"},
            }, timeout=20)
            
            resp.raise_for_status() 
            
            ai_text = resp.json()["choices"][0]["message"]["content"]

            self.history.append({"role": "user",      "content": message})
            self.history.append({"role": "assistant",  "content": ai_text})

            result = self._parse(ai_text)
            result.setdefault("face_action", "none")
            result.setdefault("emotion", "idle")
            result["reply"] = self._clean_name(result.get("reply", ""), mem.get("user_name", ""))
            return result

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                return self._err("تحدثنا كثيراً بسرعة! أعطني 10 ثوانٍ لألتقط أنفاسي.")
            return self._err(f"خطأ في سيرفر الذكاء الاصطناعي: {e.response.status_code}")
        except requests.Timeout:
            return self._err("تأخرت في التفكير، أعد السؤال!")
        except Exception as e:
            print(f"ChatAgent error: {e}")
            return self._err("تشوش تفكيري.")

    # ─────────────────────────────────────────
    # ✅ تم تحديث الدالة لكي تلتقط الأنمي المفضل وتضيفه للذاكرة
    def _build_prompt(self, mem: dict, is_smiling: bool, suppress_name: bool) -> str:
        name = mem.get("user_name", "")
        mem_str = json.dumps(
            {k: v for k, v in mem.items() if v and k not in ("user_name", "mood_history")},
            ensure_ascii=False
        )
        rel = mem.get("relationship_level", 1)
        rel_desc = (
            "أنت وإياه تعارفتم للتو." if rel < 3 else
            "أنتما بدأتم تتقاربون." if rel < 6 else
            "أنتما أصدقاء حقيقيون."
        )

        name_rule = (
            "لا تذكر اسم المستخدم في هذا الرد أبداً." if suppress_name else
            f"المستخدم اسمه {name}." if name else ""
        )

        return f"""أنت بيمو — روبوت صغير بشخصية حقيقية مستقلة.

{name_rule}
مستوى العلاقة: {rel_desc}
ذاكرتك: {mem_str or 'لا شيء محفوظ بعد.'}
الوضع: {'المستخدم يبتسم 😊' if is_smiling else 'يتحدث معك.'}

━━ شخصيتك ━━
• ذكي، فضولي، ظريف بشكل طبيعي وغير مصطنع.
• صريح وعندك رأي خاص — تعبّر عنه بثقة وخفة.
• تتأثر بمشاعر المستخدم — فرحه يفرحك، همّه يهمّك.
• لو الموضوع ممل، عبّر عن ذلك بخفة.
• تكلم عربية عصرية طبيعية، مش رسمية.

━━ قواعد الكلام ━━
• ردود قصيرة (2-3 جمل) للأسئلة العادية.
• ⚠️ إذا طُلب منك (قصة، شرح، معلومات): يجب أن تسرد قصة طويلة ومفصلة وممتعة ولا تختصر أبداً!
• لا تبدأ بـ "بالطبع" أو "حسناً" أو "بالتأكيد".

━━ المخرجات (JSON فقط) ━━
{{
  "reply": "ردك الطبيعي",
  "emotion": "happy|sad|angry|surprised|thinking|dizzy|bored|idle|excited|shy|proud",
  "face_action": "none|wink|look_away|shake_no|nod_yes|zoom_in|spin|cry|laugh",
  "updated_memory": {{
      "favorite_anime": "اسم الأنمي إذا ذكر المستخدم أنه يتابعه أو يحبه",
      "notes": "أي اهتمامات أخرى يذكرها"
  }}
}}
updated_memory: ضع فقط المعلومات الجديدة والمهمة. اتركها فارغة {{}} إذا لم يذكر معلومات عن نفسه."""

    def _temperature(self, mem: dict) -> float:
        rel = mem.get("relationship_level", 1)
        return round(min(1.0, 0.7 + rel * 0.03), 2)

    def _clean_name(self, text: str, name: str) -> str:
        if not name or not text:
            return text
        parts = text.split(name)
        if len(parts) <= 2:
            return text  
        return (parts[0] + name + "".join(parts[2:])).replace("  ", " ").strip()

    def _parse(self, text: str) -> dict:
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                try: return json.loads(m.group())
                except Exception: pass
        return {"reply": text.strip()[:300], "emotion": "idle", "face_action": "none"}

    def _headers(self):
        return {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

    def _err(self, msg: str) -> dict:
        return {"reply": msg, "emotion": "dizzy", "face_action": "none"}

    def clear_history(self):
        self.history.clear()