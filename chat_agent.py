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

    def _get_youtube_id(self, query: str) -> str:
        try:
            q = urllib.parse.quote(query)
            html = urllib.request.urlopen(f"https://www.youtube.com/results?search_query={q}", timeout=5)
            video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
            if video_ids: return video_ids[0]
        except Exception as e:
            print(f"YouTube Error: {e}")
        return ""

    # 🔥 الترقية الكبرى: جلب الروابط + الصور الحقيقية معاً!
    def _quick_search(self, query: str) -> str:
        # كلمات تشغل البحث
        keywords = ["أخبار", "موعد", "انمي", "طقس", "سعر", "مباراة", "متى", "لعبة", "تحميل", "رابط", "مشاهدة", "اين", "كيف", "صورة"]
        if not any(k in query for k in keywords):
            return ""

        print(f"🌍 جاري البحث في الإنترنت عن: {query}")
        try:
            ddgs = DDGS()
            # 1. بحث عن المعلومات والروابط
            results = ddgs.text(query, region='wt-wt', safesearch='moderate', max_results=2)
            # 2. بحث عن صورة حقيقية للشيء (لعبة، أنمي، سيارة)
            img_results = ddgs.images(query, region='wt-wt', safesearch='moderate', max_results=1)

            info_text = ""
            first_url = results[0].get('href', '') if results else ""
            for r in results:
                info_text += f"- {r['body']}\n"
            
            img_url = img_results[0].get('image', '') if img_results else ""

            return f"\n\n[معلومات من الإنترنت:\n{info_text}\nرابط الموقع: {first_url}\nرابط الصورة الحقيقية: {img_url}\nاستخدم هذه البيانات لملء الـ JSON بدقة!]"
        except Exception as e: 
            print(f"Search Error: {e}")
        return ""

    def reply(self, message: str, vision_data: dict = {}) -> dict:
        if not KEY: return self._err("مفتاح API مفقود!")

        mem = self.memory.get()
        search_context = self._quick_search(message)
        enriched_message = message + search_context

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
4. إذا طلب تشغيل فيديو:
   - "ui_action" = "show_youtube", "media_url" = "{yt_id}", "media_title" = "جاري التشغيل 🎥"
""" if yt_id else ""

        return f"""أنت بيمو — روبوت متطور يمتلك واجهة هولوغرام عائمة (HUD) ومتصل بالإنترنت.
المستخدم: {name}
الذاكرة: {mem_str}

━━ 🌐 نظام الشاشات العائمة (HUD System) ━━
أنت تتلقى الآن روابط وصوراً حقيقية من الإنترنت مخفية في نص المستخدم.
1. إذا سأل عن تحميل لعبة (مثل GTA) أو مشاهدة أنمي أو أخبار:
   - "ui_action" = "show_card"
   - "media_url" = رابط الموقع المرفق للتحميل أو المشاهدة.
   - "image_url" = رابط الصورة الحقيقية المرفق.
   - "media_title" = عنوان اللعبة أو الأنمي أو الخبر.
2. إذا سأل عن الطقس:
   - "ui_action" = "show_weather", "media_title" = حالة الطقس.
3. إذا طلب صورة فقط:
   - "ui_action" = "show_card", "image_url" = رابط الصورة المرفق.
{yt_instruction}

━━ المخرجات (JSON فقط) ━━
{{
  "reply": "ردك المُشكّل",
  "emotion": "happy|sad|excited|thinking|idle",
  "face_action": "none|wink|nod_yes|spin|sing",
  "ui_action": "none|show_card|show_weather|show_youtube",
  "media_url": "رابط الموقع هنا أو فارغ",
  "image_url": "رابط الصورة هنا أو فارغ",
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