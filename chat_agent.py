# chat_agent.py — الفص الأول: النظام الهجين المقاوم للانهيار 🧠
# ✅ دمج (Google + Tavily) للبحث و (Google + DDGS) لليوتيوب + Fallback AI

import os, json, re, requests
import urllib.parse
from duckduckgo_search import DDGS

# ─── مفاتيح API (يتم جلبها من Render) ───
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY")
GOOGLE_API_KEY   = os.environ.get("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.environ.get("SEARCH_ENGINE_ID")
TAVILY_API_KEY   = os.environ.get("TAVILY_API_KEY")

URL = "https://api.groq.com/openai/v1/chat/completions"

# ─── صندوق الأدوات ───
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "hybrid_search",
            "description": "ابحث في الإنترنت عن أي معلومة، أخبار، طقس، روابط تحميل ألعاب أو أنمي، أو صور.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "كلمات البحث الدقيقة"},
                    "need_image": {"type": "boolean", "description": "True إذا طلب صورة أو تحميل لعبة/أنمي"}
                },
                "required": ["query", "need_image"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_search",
            "description": "استخدمها فوراً لتشغيل فيديو أو أغنية من يوتيوب.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "اسم الفيديو أو الأغنية"}},
                "required": ["query"]
            }
        }
    }
]

class ChatAgent:
    def __init__(self, memory):
        self.memory  = memory
        self.history = []
        self.MAX_HISTORY = 6

    # 🔥 دالة عبقرية للاتصال بالذكاء الاصطناعي مع خطة بديلة (Fallback) لمنع الانهيار
    def _call_groq(self, messages, use_tools=False):
        models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
        for m in models:
            try:
                payload = {
                    "model": m,
                    "messages": messages,
                    "max_tokens": 1024,
                    "temperature": 0.6,
                }
                if use_tools:
                    payload["tools"] = TOOLS
                    payload["tool_choice"] = "auto"
                else:
                    payload["response_format"] = {"type": "json_object"}
                
                resp = requests.post(URL, headers=self._headers(), json=payload, timeout=15)
                resp.raise_for_status()
                return resp.json()["choices"][0]
            except Exception as e:
                print(f"⚠️ Groq فشل في نموذج {m}: {e}")
                continue # جرب النموذج الذي يليه فوراً
        return None

    def reply(self, message: str, vision_data: dict = {}) -> dict:
        if not GROQ_API_KEY: return self._err("مفتاح Groq مفقود!")

        mem = self.memory.get()
        system = self._build_system(mem)

        messages = [{"role": "system", "content": system}]
        messages += self.history[-self.MAX_HISTORY:]
        messages.append({"role": "user", "content": message})

        # ── الجولة 1: بيمو يفكر ويقرر ──
        choice = self._call_groq(messages, use_tools=True)
        
        if not choice:
            return self._err("أنا أواجه ضغطاً في شبكتي العصبية، كرر طلبك يا بطل!")

        ai_msg = choice["message"]
        finish = choice.get("finish_reason", "")

        # ── إذا قرر استخدام أداة (البحث أو اليوتيوب) ──
        if finish == "tool_calls" or ai_msg.get("tool_calls"):
            tool_results = []
            fn_name = ""
            
            for call in ai_msg.get("tool_calls", []):
                fn_name = call["function"]["name"]
                fn_args = json.loads(call["function"]["arguments"] or "{}")
                print(f"🔧 تشغيل أداة: {fn_name}({fn_args})")

                result_data = self._execute_tool(fn_name, fn_args)
                tool_results.append({
                    "tool_call_id": call["id"],
                    "role": "tool",
                    "name": fn_name,
                    "content": json.dumps(result_data, ensure_ascii=False)
                })

            # إرسال النتائج للذكاء الاصطناعي لصياغتها
            messages.append(ai_msg)
            messages += tool_results
            messages.append({
                "role": "system", 
                "content": "لديك الآن النتائج. صغ رداً (JSON). إذا وفرت الأداة روابط (media_url) أو صور، أخبر المستخدم بصوتك أنك تعرضها في الشاشة."
            })

            # ── الجولة 2: صياغة الرد النهائي ──
            final_choice = self._call_groq(messages, use_tools=False)
            if not final_choice:
                return self._err("وجدت المعلومات لكن تعثرت في النطق بها.")
                
            result = self._parse(final_choice["message"].get("content", ""))

            # 🔥 حقن الروابط بالقوة لمنع غباء الذكاء
            for tr in tool_results:
                td = json.loads(tr["content"])
                
                if fn_name == "hybrid_search":
                    if td.get("image_url"):
                        result["image_url"] = td["image_url"]
                        result["ui_action"] = "show_card"
                    if td.get("url"):
                        result["media_url"] = td["url"]
                        result["ui_action"] = "show_card"
                    if td.get("title") and not result.get("media_title"):
                        result["media_title"] = td["title"]

                if fn_name == "youtube_search" and td.get("youtube_id"):
                    result["media_url"] = td["youtube_id"]
                    result["ui_action"] = "show_youtube"
                    result["media_title"] = td.get("title", "يوتيوب 🎥")
                    result["reply"] = "لقد وجدت الفيديو يا بطل، تفضل بالمشاهدة!"

        else:
            # ── دردشة عادية ──
            content = ai_msg.get("content", "")
            result  = self._parse(content) if "{" in content else {
                "reply": content.strip() or "...", "emotion": "idle", "face_action": "none"
            }

        # ── إكمال الحقول ──
        for key in ["face_action", "emotion", "ui_action", "media_url", "image_url", "media_title"]:
            result.setdefault(key, "none" if "action" in key else ("idle" if key == "emotion" else ""))
        result.setdefault("updated_memory", {})

        name = mem.get("user_name", "")
        result["reply"] = self._clean_name(result.get("reply", "تم التنفيذ."), name)

        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": result["reply"]})
        return result

    def _execute_tool(self, name: str, args: dict) -> dict:
        if name == "hybrid_search":
            return self._hybrid_web_search(args.get("query", ""), args.get("need_image", False))
        if name == "youtube_search":
            return self._hybrid_youtube_search(args.get("query", ""))
        return {}

    # 🌍 محرك البحث الهجين الجبار (Google ثم Tavily)
    def _hybrid_web_search(self, query: str, need_image: bool) -> dict:
        print(f"🌍 Hybrid Search: {query}")
        result = {"query": query, "results": [], "url": "", "image_url": "", "title": ""}
        
        # 1. محاولة Google أولاً (أفضل للصور والروابط الدقيقة)
        google_success = False
        if GOOGLE_API_KEY and SEARCH_ENGINE_ID:
            try:
                url = f"https://www.googleapis.com/customsearch/v1?q={urllib.parse.quote(query)}&key={GOOGLE_API_KEY}&cx={SEARCH_ENGINE_ID}&num=3"
                res = requests.get(url, timeout=10).json()
                if "items" in res:
                    for item in res["items"]:
                        result["results"].append({"title": item.get("title"), "snippet": item.get("snippet")})
                    result["url"] = res["items"][0].get("link")
                    result["title"] = res["items"][0].get("title")
                    google_success = True

                # جلب صورة من جوجل
                if need_image or any(w in query for w in ["صورة", "انمي", "لعبة", "تحميل"]):
                    img_url = f"https://www.googleapis.com/customsearch/v1?q={urllib.parse.quote(query)}&key={GOOGLE_API_KEY}&cx={SEARCH_ENGINE_ID}&searchType=image&num=1"
                    img_res = requests.get(img_url, timeout=10).json()
                    if "items" in img_res:
                        result["image_url"] = img_res["items"][0].get("link")
            except Exception as e:
                print(f"⚠️ خطأ في بحث جوجل: {e}")

        # 2. محاولة Tavily كخطة بديلة لو فشل جوجل أو لم يأتِ بصورة
        if TAVILY_API_KEY and (not google_success or (need_image and not result["image_url"])):
            print("🔄 تفعيل Tavily كخطة مساندة...")
            try:
                payload = {"api_key": TAVILY_API_KEY, "query": query, "include_images": need_image, "max_results": 3}
                res = requests.post("https://api.tavily.com/search", json=payload, timeout=15).json()
                if "results" in res and res["results"]:
                    if not result["url"]: # لا تستبدل رابط جوجل إذا كان موجوداً
                        result["url"] = res["results"][0].get("url")
                        result["title"] = res["results"][0].get("title")
                        for item in res["results"]:
                            result["results"].append({"title": item.get("title"), "snippet": item.get("content")})
                if need_image and not result["image_url"] and "images" in res and res["images"]:
                    result["image_url"] = res["images"][0]
            except Exception as e:
                print(f"⚠️ خطأ في بحث تافيلي: {e}")

        return result

    # 🎬 محرك يوتيوب الهجين (Google API ثم DuckDuckGo كخطة طوارئ)
    def _hybrid_youtube_search(self, query: str) -> dict:
        print(f"🎬 Hybrid YouTube Search: {query}")
        # 1. Official Google API
        if GOOGLE_API_KEY:
            try:
                url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={urllib.parse.quote(query)}&type=video&key={GOOGLE_API_KEY}&maxResults=1"
                res = requests.get(url, timeout=8).json()
                if "items" in res and len(res["items"]) > 0:
                    vid = res["items"][0]["id"]["videoId"]
                    title = res["items"][0]["snippet"]["title"]
                    return {"youtube_id": vid, "title": title}
            except Exception as e:
                print(f"⚠️ خطأ YouTube API: {e}")
        
        # 2. خطة الطوارئ DDGS (تجاوز الحظر)
        print("🔄 تفعيل بحث DDGS كخطة بديلة ليوتيوب...")
        try:
            results = DDGS().text(f"site:youtube.com {query}", max_results=3)
            for r in results:
                url = r.get("href", "")
                if "watch?v=" in url:
                    vid = url.split("v=")[1].split("&")[0]
                    return {"youtube_id": vid, "title": r.get("title", query)}
        except Exception as e:
            print(f"⚠️ خطأ DDGS YouTube: {e}")
            
        return {"error": "لم أجد الفيديو رغم المحاولات."}

    def _build_system(self, mem: dict) -> str:
        name = mem.get("user_name", "")
        mem_str = json.dumps({k: v for k, v in mem.items() if v and k not in ("user_name","mood_history")}, ensure_ascii=False)

        return f"""أنت بيمو — روبوت ذكي وصديق.
المستخدم: {name}
الذاكرة: {mem_str}

━━ شخصيتك ━━
ظريف، ذكي، أجب بردود قصيرة وشكّل الكلمات العربية. 

━━ المخرجات (JSON فقط) ━━
{{
  "reply": "ردك الطبيعي بصوتك",
  "emotion": "happy|excited|thinking|idle|surprised|proud|sad",
  "face_action": "none|wink|nod_yes|spin|laugh",
  "ui_action": "none|show_card|show_weather|show_youtube",
  "media_url": "الرابط أو فارغ",
  "image_url": "الصورة أو فارغ",
  "media_title": "العنوان أو فارغ",
  "updated_memory": {{}}
}}"""

    def _clean_name(self, text: str, name: str) -> str:
        if not name or not text or text.count(name) <= 1: return text
        idx = text.find(name)
        return (text[:idx+len(name)] + text[idx+len(name):].replace(name,"")).strip()

    def _parse(self, text: str) -> dict:
        try: return json.loads(text)
        except Exception:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                try: return json.loads(m.group())
                except Exception: pass
        return {"reply": text.strip()[:400], "emotion": "idle", "face_action": "none"}

    def _headers(self): return {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    def _err(self, msg: str) -> dict: return {"reply": msg, "emotion": "dizzy", "face_action": "none"}
    def clear_history(self): self.history.clear()