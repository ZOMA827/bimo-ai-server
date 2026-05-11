# chat_agent.py — بيمو يفكر بنفسه 🧠 + يوتيوب موثوق 🎬
# ✅ Function Calling بدون سلاسل صلبة
# ✅ YouTube Data API v3 (موثوق 100%)
# ✅ إذا لم يجد على يوتيوب → يخبر المستخدم بدل الصمت

import os, json, re, requests
import urllib.parse
from duckduckgo_search import DDGS

KEY        = os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY")
YT_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")   # ← ضع مفتاحك هنا في Render

URL   = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

# ─── صندوق أدوات بيمو ─────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "ابحث في الإنترنت عن معلومة حقيقية تحتاج تحقق: "
                "أخبار، مواعيد إصدار، أسعار، مباريات، تفاصيل أنمي/لعبة/فيلم، طقس، شخصيات. "
                "لا تستخدمها للدردشة أو القصص أو النكت."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query":      {"type": "string",  "description": "جملة البحث"},
                    "need_image": {"type": "boolean", "description": "هل يريد المستخدم رؤية صورة؟"},
                    "need_url":   {"type": "boolean", "description": "هل نحتاج رابط المصدر؟"}
                },
                "required": ["query", "need_image", "need_url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_search",
            "description": (
                "ابحث عن فيديو أو أغنية في يوتيوب وشغّله. "
                "استخدمها عندما يطلب المستخدم فيديو أو أغنية أو مقطع صراحةً."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "اسم الفيديو أو الأغنية"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_photo",
            "description": (
                "افتح الكاميرا الأمامية والتقط صورة الآن. "
                "استخدمها فقط عندما يريد المستخدم رؤية ما أمام الكاميرا: "
                "شوفني، ما الذي تراه، انظر، ما لون قميصي. "
                "لا تستخدمها لجلب صور من الإنترنت."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]


class ChatAgent:
    def __init__(self, memory):
        self.memory  = memory
        self.history = []
        self.MAX_HISTORY = 8

    # ─── الرد الرئيسي ─────────────────────────────────────
    def reply(self, message: str, vision_data: dict = {}) -> dict:
        if not KEY:
            return self._err("مفتاح API مفقود!")

        mem      = self.memory.get()
        messages = [{"role": "system", "content": self._build_system(mem)}]
        messages += self.history[-self.MAX_HISTORY:]
        messages.append({"role": "user", "content": message})

        # ── جولة 1: بيمو يقرر هل يستخدم أداة ──────────────
        try:
            r1 = requests.post(URL, headers=self._headers(), json={
                "model":       MODEL,
                "messages":    messages,
                "tools":       TOOLS,
                "tool_choice": "auto",
                "max_tokens":  512,
                "temperature": 0.7,
            }, timeout=20)
            r1.raise_for_status()
        except Exception as e:
            print(f"Round-1 error: {e}")
            return self._err("تشوشت، حاول مرة ثانية.")

        choice = r1.json()["choices"][0]
        ai_msg = choice["message"]
        finish = choice["finish_reason"]

        # ── إذا اختار أداة ──────────────────────────────────
        if finish == "tool_calls" and ai_msg.get("tool_calls"):
            tool_results = []

            for call in ai_msg["tool_calls"]:
                fn   = call["function"]["name"]
                args = json.loads(call["function"]["arguments"] or "{}")
                print(f"🔧 بيمو يستخدم الأداة: {fn}({args})")

                # الكاميرا → إشارة فورية لـ Flutter
                if fn == "take_photo":
                    return {
                        "reply": "دعني أرى...",
                        "emotion": "thinking", "face_action": "none",
                        "ui_action": "take_photo",
                        "media_url": "", "image_url": "", "media_title": "",
                        "updated_memory": {}
                    }

                data = self._execute_tool(fn, args)
                tool_results.append({
                    "tool_call_id": call["id"],
                    "role":  "tool",
                    "name":  fn,
                    "content": json.dumps(data, ensure_ascii=False)
                })

            # ── جولة 2: بيمو يصيغ الرد بعد رؤية النتائج ────
            messages.append(ai_msg)
            messages += tool_results

            try:
                r2 = requests.post(URL, headers=self._headers(), json={
                    "model":           MODEL,
                    "messages":        messages,
                    "max_tokens":      1024,
                    "temperature":     0.85,
                    "response_format": {"type": "json_object"},
                }, timeout=20)
                r2.raise_for_status()
                ai_text = r2.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"Round-2 error: {e}")
                return self._err("وجدت النتيجة لكن تعثرت في الرد.")

            result = self._parse(ai_text)

            # حقن بيانات الأدوات إذا نسي الذكاء
            for tr in tool_results:
                td = json.loads(tr["content"])
                if td.get("error"):
                    continue
                if not result.get("image_url") and td.get("image_url"):
                    result["image_url"] = td["image_url"]
                if not result.get("media_url") and td.get("url"):
                    result["media_url"] = td["url"]
                if not result.get("media_title") and td.get("title"):
                    result["media_title"] = td["title"]
                # يوتيوب له أولوية
                if td.get("video_id"):
                    result["media_url"]   = td["video_id"]
                    result["ui_action"]   = "show_youtube"
                    result["media_title"] = td.get("title", "🎬")
                    result.setdefault("reply", f"تفضل! 🎬")

        else:
            # رد نصي عادي
            content = ai_msg.get("content", "")
            result  = self._parse(content) if "{" in content else {
                "reply": content.strip() or "...",
                "emotion": "idle", "face_action": "none", "ui_action": "none",
            }

        # ── تنظيف وإكمال الحقول ────────────────────────────
        for k, v in [
            ("face_action","none"), ("emotion","idle"), ("ui_action","none"),
            ("media_url",""), ("image_url",""), ("media_title",""), ("updated_memory",{})
        ]:
            result.setdefault(k, v)

        result["reply"] = self._clean_name(
            result.get("reply","..."), mem.get("user_name","")
        )
        if not result["reply"] or len(result["reply"]) < 2:
            result["reply"] = "نفذت طلبك، انظر الشاشة!"

        self.history.append({"role": "user",      "content": message})
        self.history.append({"role": "assistant",  "content": result["reply"]})
        print(f"🤖 {result['reply'][:80]}")
        return result

    # ─── تنفيذ الأدوات ────────────────────────────────────
    def _execute_tool(self, name: str, args: dict) -> dict:
        if name == "web_search":
            return self._web_search(args["query"], args.get("need_image", False))
        if name == "youtube_search":
            return self._youtube_search(args["query"])
        return {}

    # ─── بحث الويب ───────────────────────────────────────
    def _web_search(self, query: str, need_image: bool) -> dict:
        print(f"🌍 بحث: '{query}' | صورة={need_image}")
        out = {"query": query, "results": [], "url": "", "image_url": "", "title": ""}
        try:
            ddgs  = DDGS()
            texts = ddgs.text(query, region="wt-wt", safesearch="moderate", max_results=4)
            out["results"] = [
                {"title": r.get("title",""), "body": r.get("body",""), "url": r.get("href","")}
                for r in texts
            ]
            for r in texts:
                if r.get("href","").startswith("http"):
                    out["url"]   = r["href"]
                    out["title"] = r.get("title","")
                    break

            if need_image:
                imgs = ddgs.images(query, region="wt-wt", safesearch="moderate", max_results=8)
                for img in imgs:
                    u = img.get("image","")
                    if u and re.search(r'\.(jpg|jpeg|png|webp)(\?|$)', u, re.I):
                        out["image_url"] = u
                        break
        except Exception as e:
            print(f"Search error: {e}")
            out["error"] = str(e)
        return out

    # ─── بحث يوتيوب (3 طرق بالترتيب) ────────────────────
    def _youtube_search(self, query: str) -> dict:
        print(f"🎬 يوتيوب: '{query}'")

        # الطريقة 1: YouTube Data API v3 (الأفضل لو عندك مفتاح)
        if YT_API_KEY:
            result = self._yt_api_v3(query)
            if result.get("video_id"):
                print(f"✅ يوتيوب API: {result['video_id']}")
                return result

        # الطريقة 2: DuckDuckGo يبحث داخل يوتيوب
        result = self._yt_via_duckduckgo(query)
        if result.get("video_id"):
            print(f"✅ يوتيوب DDG: {result['video_id']}")
            return result

        # الطريقة 3: YouTube search page (scraping)
        result = self._yt_via_scrape(query)
        if result.get("video_id"):
            print(f"✅ يوتيوب Scrape: {result['video_id']}")
            return result

        print(f"❌ ما وجدت فيديو: '{query}'")
        return {"error": f"ما وجدت فيديو يوتيوب لـ '{query}' الآن، جرب لاحقاً."}

    def _yt_api_v3(self, query: str) -> dict:
        """YouTube Data API v3 — أدق وأسرع"""
        try:
            params = urllib.parse.urlencode({
                "part":       "snippet",
                "q":          query,
                "type":       "video",
                "maxResults": "1",
                "key":        YT_API_KEY,
            })
            r = requests.get(
                f"https://www.googleapis.com/youtube/v3/search?{params}",
                timeout=8
            )
            if r.status_code == 200:
                items = r.json().get("items", [])
                if items:
                    vid_id = items[0]["id"].get("videoId","")
                    title  = items[0]["snippet"].get("title","")
                    if vid_id:
                        return {"video_id": vid_id, "title": title}
        except Exception as e:
            print(f"YT API v3 error: {e}")
        return {}

    def _yt_via_duckduckgo(self, query: str) -> dict:
        """DuckDuckGo يبحث في يوتيوب ويرجع رابط watch"""
        try:
            ddgs    = DDGS()
            results = ddgs.text(
                f"{query} site:youtube.com/watch",
                region="wt-wt", safesearch="off", max_results=5
            )
            for r in results:
                url = r.get("href","")
                m   = re.search(r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})', url)
                if m:
                    return {"video_id": m.group(1), "title": r.get("title", query)}
        except Exception as e:
            print(f"DDG YT error: {e}")
        return {}

    def _yt_via_scrape(self, query: str) -> dict:
        """scraping صفحة يوتيوب — آخر خيار"""
        try:
            q   = urllib.parse.quote(query)
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            r    = requests.get(
                f"https://www.youtube.com/results?search_query={q}&sp=EgIQAQ%3D%3D",
                headers=headers, timeout=10
            )
            html = r.text

            # استخراج الـ video IDs بطريقتين
            ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
            # حذف المكررات مع الحفاظ على الترتيب
            seen, unique = set(), []
            for i in ids:
                if i not in seen:
                    seen.add(i)
                    unique.append(i)

            if unique:
                vid_id = unique[0]
                # حاول تجيب العنوان
                title_matches = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"', html)
                title = title_matches[0] if title_matches else query
                return {"video_id": vid_id, "title": title}
        except Exception as e:
            print(f"Scrape YT error: {e}")
        return {}

    # ─── رسالة النظام ─────────────────────────────────────
    def _build_system(self, mem: dict) -> str:
        name    = mem.get("user_name","")
        mem_str = json.dumps(
            {k: v for k,v in mem.items() if v and k not in ("user_name","mood_history")},
            ensure_ascii=False
        )
        return f"""أنت بيمو — روبوت ذكي وصديق حقيقي.
{"المستخدم اسمه " + name + "." if name else ""}
ذاكرتك: {mem_str}

━━ شخصيتك ━━
ظريف، ذكي، فضولي، صريح. لا تبدأ بـ "بالطبع" أو "حسناً".
لا تكرر الاسم أكثر من مرة. رد بلغة المستخدم تلقائياً.

━━ أدواتك — أنت تقرر متى تستخدم كل واحدة ━━
• web_search    ← معلومات تحتاج تحقق (أخبار، مواعيد، تفاصيل، أسعار)
• youtube_search ← فيديو/أغنية طلبها المستخدم صراحة
• take_photo    ← رؤية ما أمام الكاميرا (ليس لجلب صور من الإنترنت)

━━ بعد استخدام أداة، أجب بـ JSON فقط ━━
{{
  "reply": "ردك الطبيعي — تكلم دائماً",
  "emotion": "happy|excited|thinking|idle|surprised|proud|sad|bored",
  "face_action": "none|wink|nod_yes|spin|laugh",
  "ui_action": "none|show_card|show_weather|show_youtube",
  "media_url": "https://... أو video_id أو فارغ",
  "image_url": "https://... أو فارغ",
  "media_title": "عنوان قصير أو فارغ",
  "updated_memory": {{}}
}}

━━ دردشة عادية ━━
نفس JSON لكن ui_action: none — لا تستخدم أداة أبداً."""

    # ─── مساعدات ──────────────────────────────────────────
    def _clean_name(self, text: str, name: str) -> str:
        if not name or not text or text.count(name) <= 1:
            return text
        idx = text.find(name)
        return (text[:idx+len(name)] + text[idx+len(name):].replace(name,"")).strip()

    def _parse(self, text: str) -> dict:
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                try: return json.loads(m.group())
                except Exception: pass
        return {"reply": text.strip()[:400], "emotion": "idle", "face_action": "none"}

    def _headers(self):
        return {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

    def clear_history(self):
        self.history.clear()

    def _err(self, msg: str) -> dict:
        return {"reply": msg, "emotion": "dizzy", "face_action": "none",
                "ui_action": "none", "media_url": "", "image_url": "", "media_title": ""}
