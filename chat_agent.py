# chat_agent.py — الفص الأول: وكيل الحوار السريع + محرك البحث 🌍
# ✅ تم التحديث إلى Llama 3.1 8B Instant + DuckDuckGo Search

import os, json, re, requests
from duckduckgo_search import DDGS # 🔥 استدعاء محرك البحث

KEY = os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY")
URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

class ChatAgent:
    def __init__(self, memory):
        self.memory = memory
        self.history = []
        self.MAX_HISTORY = 6 

    # 🔥 دالة البحث السريع في الإنترنت
    def _quick_search(self, query: str) -> str:
        # الكلمات المفتاحية التي تستدعي البحث
        keywords = ["أخبار", "موعد", "انمي", "أنمي", "طقس", "من هو", "ما هي", "سعر", "مباراة", "نتيجة", "حدث", "جديد"]
        if not any(k in query for k in keywords):
            return "" # حوار عادي لا يحتاج بحث

        print(f"🌍 جاري البحث في الإنترنت عن: {query}")
        try:
            # جلب أهم نتيجتين من الإنترنت
            results = DDGS().text(query, region='wt-wt', safesearch='moderate', max_results=2)
            if results:
                info_text = ""
                first_url = results[0].get('href', '')
                for r in results:
                    info_text += f"- {r['body']}\n"
                
                return f"\n\n[عقلك الباحث وجد هذه المعلومات الحية الآن في الإنترنت:\n{info_text}\nرابط المصدر: {first_url}\nاستخدم هذه المعلومات للرد، واستخدم الرابط إذا أردت عرض نافذة أخبار]."
        except Exception as e:
            print(f"⚠️ فشل البحث: {e}")
        return ""

    def reply(self, message: str, vision_data: dict = {}) -> dict:
        if not KEY:
            return self._err("مفتاح API مفقود!")

        mem = self.memory.get()
        is_smiling = vision_data.get("is_user_smiling", False)
        suppress_name = vision_data.get("suppress_name", False)

        system = self._build_prompt(mem, is_smiling, suppress_name)

        # 🔥 تفعيل البحث قبل إرسال الرسالة للذكاء الاصطناعي
        search_context = self._quick_search(message)
        enriched_message = message + search_context

        messages = [{"role": "system", "content": system}]
        for m in self.history[-self.MAX_HISTORY:]:
            messages.append(m)
        messages.append({"role": "user", "content": enriched_message}) # إرسال السؤال + نتائج البحث!

        try:
            resp = requests.post(URL, headers=self._headers(), json={
                "model": MODEL,
                "messages": messages,
                "max_tokens": 1024,
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
            result.setdefault("ui_action", "none")
            result["reply"] = self._clean_name(result.get("reply", ""), mem.get("user_name", ""))
            return result

        except Exception as e:
            print(f"ChatAgent error: {e}")
            return self._err("تشوش تفكيري.")

    def _build_prompt(self, mem: dict, is_smiling: bool, suppress_name: bool) -> str:
        name = mem.get("user_name", "")
        mem_str = json.dumps({k: v for k, v in mem.items() if v and k not in ("user_name", "mood_history")}, ensure_ascii=False)
        rel = mem.get("relationship_level", 1)

        return f"""أنت بيمو — روبوت متطور يمتلك واجهة هولوغرام عائمة (HUD) ومتصل بالإنترنت.
المستخدم: {name}
الذاكرة: {mem_str}

━━ شخصيتك وقواعد النطق ━━
• أنت تتحدث مع شاب (رجل ذكر)، فخاطبه دائماً بصيغة المذكر (يا بطل، مستعد، إلخ).
• ⚠️ قاعدة النطق: شكّل الكلمات العربية بالحركات.

━━ 🌐 نظام الشاشات العائمة والإنترنت (HUD System) ━━
إذا وفرت لك معلومات من الإنترنت (في نص رسالة المستخدم):
1. أجب عن سؤاله باستخدام تلك المعلومات.
2. اجعل "ui_action" = "show_news"
3. ضع في "media_url" رابط المصدر الذي وفرته لك.
4. ضع في "media_title" عنواناً جذاباً للخبر أو المعلومة.

إذا طلب رؤية صورة (مثال: أرني سيارة، قطة):
- "ui_action" = "show_image"
- "media_url" = "https://image.pollinations.ai/prompt/NAME" (استبدل NAME باسم الشيء بالإنجليزية).
- "media_title" = وصف قصير.

━━ المخرجات (JSON فقط) ━━
{{
  "reply": "ردك المُشكّل والمبني على معلومات الإنترنت إن وُجدت",
  "emotion": "happy|sad|angry|surprised|thinking|dizzy|bored|idle|excited|shy|proud",
  "face_action": "none|wink|look_away|shake_no|nod_yes|zoom_in|spin|cry|laugh|sing",
  "ui_action": "none|show_image|show_news",
  "media_url": "الرابط هنا أو فارغ",
  "media_title": "العنوان هنا أو فارغ",
  "updated_memory": {{}}
}}"""

    def _temperature(self, mem: dict) -> float:
        rel = mem.get("relationship_level", 1)
        return round(min(1.0, 0.7 + rel * 0.03), 2)

    def _clean_name(self, text: str, name: str) -> str:
        if not name or not text: return text
        parts = text.split(name)
        if len(parts) <= 2: return text  
        return (parts[0] + name + "".join(parts[2:])).replace("  ", " ").strip()

    def _parse(self, text: str) -> dict:
        try: return json.loads(text)
        except:
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                try: return json.loads(m.group())
                except: pass
        return {"reply": text.strip()[:300], "emotion": "idle", "face_action": "none"}

    def _headers(self):
        return {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

    def clear_history(self):
        self.history.clear()

    def _err(self, msg: str) -> dict:
        return {"reply": msg, "emotion": "dizzy", "face_action": "none"}
