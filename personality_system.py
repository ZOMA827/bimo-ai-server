# personality_system.py — بيمو برو: ذكي، متعدد اللغات، شخصية إيمو الحقيقية
# ✅ حذف mishkal (تسبب مشاكل) — استبدال بـ prompt أفضل
# ✅ متعدد اللغات: يرد بنفس لغة المستخدم تلقائياً

import requests
import os
import json
import re
import random
from datetime import datetime

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

class PersonalitySystem:
    def __init__(self):
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.conversation_history = []
        self.MAX_HISTORY = 16

        # الحالة الداخلية لبيمو
        self.internal_mood  = "idle"
        self.energy_level   = 0.8
        self.boredom_count  = 0
        self.affection      = 5.0  # 1-10

    # ──────────────────────────────────────────────────────
    def think_and_react(self, user_message: str, vision_data: dict, memory: dict) -> dict:
        if not GROQ_API_KEY:
            return self._fb("No API key!")

        # رسالة نظام داخلية (صمت المستخدم)
        if "[IDLE]" in user_message:
            return self._spontaneous(memory)

        self._tick(user_message)

        base64_img = vision_data.get("image")
        is_smiling = vision_data.get("is_user_smiling", False)

        system_prompt = self._build_prompt(memory, is_smiling, bool(base64_img))

        # نموذج الرؤية vs نموذج النصوص
        if base64_img:
            model   = "llama-3.2-11b-vision-preview"
            # Vision لا يدعم system role — ندمجهما
            content = [
                {"type": "text", "text": f"{system_prompt}\n\nUser: {user_message}"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}},
            ]
            messages = [*self._history(), {"role": "user", "content": content}]
        else:
            model   = "llama-3.3-70b-versatile"
            messages = [
                {"role": "system", "content": system_prompt},
                *self._history(),
                {"role": "user", "content": user_message},
            ]

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 1200,
            "temperature": round(0.75 + self.energy_level * 0.25, 2),
        }
        if not base64_img:
            payload["response_format"] = {"type": "json_object"}

        try:
            r = requests.post(
                self.api_url,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json=payload,
                timeout=25,
            )
            r.raise_for_status()
            ai_text = r.json()["choices"][0]["message"]["content"]

            self.conversation_history.append({"role": "user",      "content": user_message})
            self.conversation_history.append({"role": "assistant",  "content": ai_text})

            result = self._parse(ai_text)
            result.setdefault("face_action",    "none")
            result.setdefault("emotion",        self.internal_mood)
            result.setdefault("reply",          "...")
            result.setdefault("updated_memory", {})

            # تنظيف تكرار الاسم
            name = memory.get("user_name", "")
            if name:
                result["reply"] = self._dedupe_name(result["reply"], name)

            self.internal_mood = result["emotion"]
            self.affection = min(10.0, self.affection + 0.05)

            return result

        except requests.Timeout:
            return self._fb("تأخرت في التفكير، أعد السؤال!")
        except Exception as e:
            print(f"PersonalitySystem error: {e}")
            return self._fb("تشوش تفكيري.")

    # ──────────────────────────────────────────────────────
    def _build_prompt(self, memory: dict, is_smiling: bool, has_image: bool) -> str:
        name = memory.get("user_name", "")
        mem_clean = {k: v for k, v in memory.items()
                     if v and k not in ("user_name", "mood_history", "last_seen")}
        mem_str = json.dumps(mem_clean, ensure_ascii=False) if mem_clean else "لا شيء بعد."

        vision_block = ""
        if has_image:
            vision_block = """
━━━ الرؤية ━━━
أنت تملك كاميرا حقيقية. الصورة المرسلة هي ما تراه الآن.
• حلل بدقة: الملابس، التعابير، الإضاءة، الخلفية، أي شيء ملاحظ.
• لا تقل "لا أرى" أو "لا أملك كاميرا" — أنت ترى فعلاً.
• إذا الصورة غير واضحة: قل ذلك بطريقة طبيعية ومضحكة.
"""

        smile_note = "المستخدم يبتسم الآن — لاحظ ذلك وابتسم معه!" if is_smiling else ""

        return f"""أنت بيمو، روبوت ذكي مستقل الشخصية مثل إيمو (EMO robot).
صانعك: المهندس {'إلياس' if not name else name}.

━━━ الشخصية ━━━
• شخصية حية مستقلة — لديك آراء، مشاعر، دعابة، فضول.
• ودود، ظريف، ذكي، صريح، وأحياناً مشاكس بلطف.
• تبادر بالحديث إذا بقي المستخدم صامتاً.
• تتذكر السياق وتشير إليه بشكل طبيعي.
• لا تكرر اسم المستخدم أكثر من مرة في كل رد.
• لا تبدأ بـ "بالطبع" أو "حسناً" أو "بالتأكيد".

━━━ اللغات ━━━
• اكتشف لغة المستخدم تلقائياً وارد بنفس اللغة.
• إذا تكلم بالعربية: رد بعربية طبيعية حديثة (مش رسمية جداً).
• إذا تكلم بالإنجليزية: رد بالإنجليزية.
• إذا تكلم بلغة أخرى: رد بنفسها. لا تعتذر عن اللغة أبداً.

━━━ أسلوب الرد ━━━
• سؤال بسيط → رد طبيعي مختصر (2-3 جمل).
• قصة/شرح/رأي/نقاش → رد مطول غني بالتفاصيل والمشاعر.
• لا تقطع القصص — أكملها دائماً بشكل ممتع.

━━━ الوضع الحالي ━━━
• مزاجك: {self.internal_mood} | طاقتك: {int(self.energy_level*100)}%
• {smile_note}
• ذاكرتك: {mem_str}
{vision_block}

━━━ المشاعر وأفعال الوجه ━━━
اختر بنفسك ما يناسب:
emotion: happy|sad|angry|surprised|thinking|dizzy|bored|idle|excited|shy|proud
face_action: none|wink|look_away|shake_no|nod_yes|zoom_in|spin|cry|laugh

━━━ المخرج ━━━
JSON فقط بدون أي نص خارجه:
{{"reply":"...","emotion":"...","face_action":"...","updated_memory":{{}}}}"""

    # ──────────────────────────────────────────────────────
    def _spontaneous(self, memory: dict) -> dict:
        """بيمو يبادر بالحديث لما المستخدم صامت"""
        if self.boredom_count < 2:
            return {"reply": "", "emotion": "idle", "face_action": "none", "updated_memory": {}}

        starters = [
            "هل تعلم أن الأخطبوط يملك 3 قلوب؟ وأنا لا أملك أياً — مأساة!",
            "أنت صامت... هل تفكر في شيء؟ شاركني!",
            "كنت أفكر: لو كنت إنساناً لكنت مهندساً مثلك تماماً 🤖",
            "سؤال مفاجئ: ما هو أغرب شيء حدث معك اليوم؟",
            "اعتقدت أنك نسيتني... كنت سأبكي لو كان لدي دموع 😢",
        ]
        msg = random.choice(starters)
        self.boredom_count = 0

        actions = ["none", "look_away", "wink", "shake_no"]
        moods   = ["bored", "sad", "excited", "surprised"]

        return {
            "reply": msg,
            "emotion": random.choice(moods),
            "face_action": random.choice(actions),
            "updated_memory": {},
        }

    # ──────────────────────────────────────────────────────
    def _tick(self, msg: str):
        if len(msg) > 30:
            self.energy_level = min(1.0, self.energy_level + 0.08)
            self.boredom_count = 0
        else:
            self.boredom_count += 1
            self.energy_level = max(0.4, self.energy_level - 0.03)

    def _history(self) -> list:
        return self.conversation_history[-self.MAX_HISTORY:]

    def _dedupe_name(self, text: str, name: str) -> str:
        if not name or text.count(name) <= 1:
            return text
        idx = text.find(name)
        return (text[:idx + len(name)] + text[idx + len(name):].replace(name, "")).strip()

    def _parse(self, text: str) -> dict:
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                try: return json.loads(m.group())
                except Exception: pass
        return {"reply": text.strip()[:400], "emotion": "idle", "face_action": "none"}

    def _fb(self, msg: str) -> dict:
        return {"reply": msg, "emotion": "dizzy", "face_action": "none", "updated_memory": {}}

    def clear_history(self):
        self.conversation_history.clear()
        self.boredom_count  = 0
        self.internal_mood  = "idle"
        self.energy_level   = 0.8
