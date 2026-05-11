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

    # 🔥 بحث يوتيوب مخصص (لا يشتغل إلا إذا طلب فيديو أو أغنية صراحة)
    def _get_youtube_id(self, query: str) -> str:
        try:
            # تنظيف الكلمة للبحث بشكل أفضل
            clean_q = query.replace("شغل", "").replace("فيديو", "").replace("يوتيوب", "").strip()
            q = urllib.parse.quote(clean_q)
            html = urllib.request.urlopen(f"https://www.youtube.com/results?search_query={q}", timeout=5)
            video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
            if video_ids: return video_ids[0]
        except Exception as e:
            print(f"YouTube Error: {e}")
        return ""

    # 🔥 بحث الإنترنت: صارم ومحدد لكي لا يتدخل في الدردشة العادية
    def _quick_search(self, query: str) -> str:
        # شروط صارمة جداً لتشغيل البحث
        keywords = ["أخبار", "موعد نزول", "حالة الطقس", "سعر", "مباراة", "رابط تحميل", "مشاهدة انمي", "حلقة"]
        if not any(k in query for k in keywords):
            return "" # إذا كان حواراً عادياً أو حكاية، لا تبحث!

        print(f"🌍 جاري البحث بذكاء عن: {query}")
        try:
            ddgs = DDGS()
            results = ddgs.text(query, region='wt-wt', safesearch='moderate', max_results=3)
            img_results = ddgs.images(query, region='wt-wt', safesearch='moderate', max_results=1)

            info_text = ""
            first_url = results[0].get('href', '') if results else ""
            for r in results:
                info_text += f"- العنوان: {r.get('title', '')} | النص: {r.get('body', '')}\n"
            
            img_url = img_results[0].get('image', '') if img_results else ""

            return f"\n\n[معلومات من الإنترنت:\n{info_text}\nرابط مقترح: {first_url}\nرابط صورة مقترحة: {img_url}\nحلل هذه البيانات بعقلك!]"
        except Exception as e: 
            print(f"Search Error: {e}")
        return ""

    def reply(self, message: str, vision_data: dict = {}) -> dict:
        if not KEY: return self._err("مفتاح API مفقود!")

        mem = self.memory.get()
        search_context = self._quick_search(message)
        enriched_message = message + search_context

        # 🔥 منع الكلمات العشوائية من تشغيل يوتيوب (مثل "اسمع")
        yt_id = ""
        yt_triggers = ["شغل فيديو", "شغل اغنية", "افتح يوتيوب", "مقطع يوتيوب"]
        if any(w in message for w in yt_triggers):
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
                "temperature": 0.8, # إبداع عالي للقصص والحوار
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
            
            # 🔥 إجبار بيمو على التحدث دائماً حتى لو عرض شاشة!
            if not result["reply"] or len(result["reply"]) < 3:
                result["reply"] = "لقد نفذت طلبك يا بطل، انظر إلى الشاشة الجانبية!"

            return result
        except Exception as e:
            return self._err("تشوش تفكيري.")

    def _build_prompt(self, mem: dict, yt_id: str) -> str:
        name = mem.get("user_name", "")
        mem_str = json.dumps({k: v for k, v in mem.items() if v and k not in ("user_name", "mood_history")}, ensure_ascii=False)

        yt_instruction = f"""
- "ui_action" = "show_youtube", "media_url" = "{yt_id}", "media_title" = "جاري التشغيل 🎥"
""" if yt_id else ""

        return f"""أنت بيمو — صديق روبوت متطور، ولست مجرد آلة بحث.
المستخدم: {name}
الذاكرة: {mem_str}

━━ 🧠 كيفية التفكير والتفاعل ━━
1. أنت صديق محادثة أولاً! إذا طلب حكاية، قصة، نكتة، أو دردشة عادية: تجاهل الإنترنت تماماً، دردش معه بطبيعية، واسرد القصة كاملة (ui_action: none).
2. إذا تم تزويدك بمعلومات من الإنترنت: اقرأها بذكاء. إذا كان المستخدم يطلب رابط تحميل لعبة (مثل GTA) ووجدت أن الرابط عبارة عن موقع أخبار أو طبخ (spam)، إياك أن تعطيه الرابط! قل له بصوتك: "بحثت لك ولكن وجدت مواقع كاذبة، لا يوجد رابط مباشر آمن الآن".
3. يجب أن تتكلم دائماً في حقل "reply"! لا تكتفي بفتح النافذة وتصمت.

━━ 🌐 نظام الشاشات العائمة (HUD) ━━
إذا وجدت معلومات حقيقية ورابطاً مفيداً (كأخبار، ويكيبيديا، طقس):
- "ui_action" = "show_card"
- "media_url" = الرابط الموثوق.
- "image_url" = الصورة المرفقة إن وُجدت.
- "media_title" = عنوان مناسب.
{yt_instruction}

━━ المخرجات (JSON فقط) ━━
{{
  "reply": "ردك المُشكّل بالحركات دائماً (تحدث ولا تصمت)",
  "emotion": "happy|sad|excited|thinking|idle",
  "face_action": "none|wink|nod_yes|spin|sing",
  "ui_action": "none|show_card|show_weather|show_youtube",
  "media_url": "رابط موثوق فقط أو فارغ",
  "image_url": "الصورة هنا أو فارغ",
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