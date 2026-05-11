# chat_agent.py — الفص الأول: وكيل الحوار + محرك البحث المتطور 🌍
import os, json, re, requests
import urllib.request, urllib.parse
from duckduckgo_search import DDGS

KEY = os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY")
URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

class ChatAgent:
    def __init__(self, memory):
        self.memory = memory
        self.history = []
        self.MAX_HISTORY = 6 

    # 🔥 أداة سحرية للبحث في يوتيوب وجلب الـ ID مباشرة!
    def _get_youtube_id(self, query: str) -> str:
        try:
            q = urllib.parse.quote(query)
            html = urllib.request.urlopen(f"https://www.youtube.com/results?search_query={q}", timeout=5)
            video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
            if video_ids:
                return video_ids[0] # إرجاع الـ ID الحقيقي
        except Exception as e:
            print(f"YouTube Error: {e}")
        return ""

    def _quick_search(self, query: str) -> str:
        keywords = ["أخبار", "موعد", "انمي", "طقس", "من هو", "ما هي", "سعر", "مباراة", "متى"]
        if not any(k in query for k in keywords):
            return ""

        print(f"🌍 جاري البحث في الإنترنت عن: {query}")
        try:
            results = DDGS().text(query, region='wt-wt', safesearch='moderate', max_results=2)
            if results:
                info_text = ""
                first_url = results[0].get('href', '')
                for r in results:
                    info_text += f"- {r['body']}\n"
                return f"\n\n[معلومات من الإنترنت:\n{info_text}\nرابط: {first_url}\nاستخدمها لتجيب بدقة.]"
        except: pass
        return ""

    def reply(self, message: str, vision_data: dict = {}) -> dict:
        if not KEY: return self._err("مفتاح API مفقود!")

        mem = self.memory.get()
        search_context = self._quick_search(message)
        enriched_message = message + search_context

        # إذا طلب فيديو يوتيوب أو أغنية، نبحث عنها بالبايثون ونجلب الـ ID
        yt_id = ""
        if any(w in message for w in ["فيديو", "يوتيوب", "اغنية", "شغل", "اسمع"]):
            yt_id = self._get_youtube_id(message)

        system = self._build_prompt(mem, yt_id)

        messages = [{"role": "system", "content": system}]
        for m in self.history[-self.MAX_HISTORY:]:
            messages.append(m)
        messages.append({"role": "user", "content": enriched_message})

        try:
            resp = requests.post(URL, headers=self._headers(), json={
                "model": MODEL,
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.8,
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
            return self._err("تشوش تفكيري.")

    def _build_prompt(self, mem: dict, yt_id: str) -> str:
        name = mem.get("user_name", "")
        mem_str = json.dumps({k: v for k, v in mem.items() if v and k not in ("user_name", "mood_history")}, ensure_ascii=False)

        yt_instruction = f"""
4. إذا طلب تشغيل فيديو أو أغنية:
   - اجعل "ui_action" = "show_youtube"
   - ضع في "media_url" هذا المعرف الحرفي: "{yt_id}"
   - ضع في "media_title" = "جاري تشغيل الفيديو 🎥"
""" if yt_id else ""

        return f"""أنت بيمو — روبوت متطور يمتلك واجهة هولوغرام عائمة (HUD) ومتصل بالإنترنت.
المستخدم: {name}
الذاكرة: {mem_str}

━━ شخصيتك وقواعد النطق ━━
• خاطبه دائماً بصيغة المذكر.
• ⚠️ قاعدة النطق: شكّل الكلمات العربية بالحركات.

━━ 🌐 نظام الشاشات العائمة والإنترنت (HUD System) ━━
1. إذا سأل عن أخبار أو مواعيد ووجدت لك معلومات من الإنترنت:
   - "ui_action" = "show_news"
   - "media_url" = رابط المصدر المرفق.
   - "media_title" = عنوان جذاب للخبر.
2. إذا سأل عن الطقس:
   - "ui_action" = "show_weather"
   - "media_title" = اكتب درجة الحرارة وحالة الطقس (مثال: الطقس غائم 25°C).
3. إذا طلب رؤية صورة:
   - "ui_action" = "show_image"
   - "media_url" = "https://image.pollinations.ai/prompt/NAME" (استبدل NAME بالشيء بالإنجليزية).
   - "media_title" = وصف الصورة.
{yt_instruction}

━━ المخرجات (JSON فقط) ━━
{{
  "reply": "ردك المُشكّل",
  "emotion": "happy|sad|angry|surprised|thinking|dizzy|bored|idle|excited|shy|proud",
  "face_action": "none|wink|look_away|shake_no|nod_yes|zoom_in|spin|cry|laugh|sing",
  "ui_action": "none|show_image|show_news|show_weather|show_youtube",
  "media_url": "الرابط هنا أو فارغ",
  "media_title": "العنوان هنا أو فارغ",
  "updated_memory": {{}}
}}"""

    def _clean_name(self, text: str, name: str) -> str:
        if not name or not text: return text
        parts = text.split(name)
        return text if len(parts) <= 2 else (parts[0] + name + "".join(parts[2:])).replace("  ", " ").strip()

    def _parse(self, text: str) -> dict:
        try: return json.loads(text)
        except:
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                try: return json.loads(m.group())
                except: pass
        return {"reply": text.strip()[:300], "emotion": "idle", "face_action": "none"}

    def _headers(self): return {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    def clear_history(self): self.history.clear()
    def _err(self, msg: str) -> dict: return {"reply": msg, "emotion": "dizzy", "face_action": "none"}