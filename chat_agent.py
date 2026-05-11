# chat_agent.py — الفص الأول: بيمو يفكر بنفسه بدون سلاسل 🧠
# ✅ Function Calling: الذكاء يقرر متى يبحث، متى يجلب صورة، متى يشغل يوتيوب
# ✅ لا يوجد أي قائمة keywords صلبة — بيمو يفهم النية

import os, json, re, requests
import urllib.request, urllib.parse
from duckduckgo_search import DDGS

KEY   = os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY")
URL   = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"   # 70b يدعم tool_calling بشكل أفضل

# ─── صندوق أدوات بيمو ─────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "ابحث في الإنترنت عن أي معلومة حقيقية تحتاج تحقق أو تحديث: "
                "أخبار، مواعيد إصدار، أسعار، مباريات، تفاصيل أنمي أو لعبة أو فيلم، "
                "طقس، شخصيات، أحداث حالية. "
                "لا تستخدمها للدردشة العادية أو القصص أو النكت."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "جملة البحث المثالية بالعربية أو الإنجليزية"
                    },
                    "need_image": {
                        "type": "boolean",
                        "description": "هل المستخدم يريد رؤية صورة مع المعلومة؟"
                    },
                    "need_url": {
                        "type": "boolean",
                        "description": "هل نحتاج رابط المصدر لعرضه في الشاشة العائمة؟"
                    }
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
                "ابحث عن فيديو أو أغنية في يوتيوب وشغّله مباشرة. "
                "استخدمها فقط عندما يطلب المستخدم صراحة تشغيل فيديو أو أغنية."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "اسم الأغنية أو الفيديو للبحث عنه"
                    }
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
                "افتح الكاميرا الأمامية والتقط صورة. "
                "استخدمها فقط عندما يطلب المستخدم رؤية ما أمام الكاميرا أو وصف محيطه، "
                "مثل: شوفني، ما الذي تراه، انظر، ما لون قميصي. "
                "لا تستخدمها عندما يطلب صورة من الإنترنت كصورة أنمي أو سيارة."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
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

        mem    = self.memory.get()
        system = self._build_system(mem)

        messages = [{"role": "system", "content": system}]
        messages += self.history[-self.MAX_HISTORY:]
        messages.append({"role": "user", "content": message})

        # ── الجولة الأولى: بيمو يقرر هل يستخدم أداة ──────
        try:
            resp = requests.post(URL, headers=self._headers(), json={
                "model":       MODEL,
                "messages":    messages,
                "tools":       TOOLS,
                "tool_choice": "auto",
                "max_tokens":  1024,
                "temperature": 0.7,
            }, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            print(f"ChatAgent Round-1 error: {e}")
            return self._err("تشوشت قليلاً، حاول مرة ثانية.")

        choice  = resp.json()["choices"][0]
        ai_msg  = choice["message"]
        finish  = choice["finish_reason"]

        # ── لو قرر يستخدم أداة ────────────────────────────
        if finish == "tool_calls" and ai_msg.get("tool_calls"):
            tool_results = []

            for call in ai_msg["tool_calls"]:
                fn_name = call["function"]["name"]
                fn_args = json.loads(call["function"]["arguments"] or "{}")
                print(f"🔧 بيمو يستخدم: {fn_name}({fn_args})")

                # لو طلب الكاميرا → أرجع إشارة لـ Flutter فوراً
                if fn_name == "take_photo":
                    return {
                        "reply":          "دعني أرى...",
                        "emotion":        "thinking",
                        "face_action":    "none",
                        "ui_action":      "take_photo",
                        "media_url":      "",
                        "image_url":      "",
                        "media_title":    "",
                        "updated_memory": {}
                    }

                result_data = self._execute_tool(fn_name, fn_args)
                tool_results.append({
                    "tool_call_id": call["id"],
                    "role":         "tool",
                    "name":         fn_name,
                    "content":      json.dumps(result_data, ensure_ascii=False)
                })

            # ── الجولة الثانية: بيمو يصيغ رده بعد النتائج ──
            messages.append(ai_msg)
            messages += tool_results

            try:
                resp2 = requests.post(URL, headers=self._headers(), json={
                    "model":       MODEL,
                    "messages":    messages,
                    "max_tokens":  1024,
                    "temperature": 0.8,
                    "response_format": {"type": "json_object"},
                }, timeout=20)
                resp2.raise_for_status()
                ai_text = resp2.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"ChatAgent Round-2 error: {e}")
                return self._err("وجدت المعلومة لكن تعثرت في صياغة الرد.")

            result = self._parse(ai_text)

            # حقن بيانات الأدوات لو الذكاء نسي يضعها
            for tr in tool_results:
                td = json.loads(tr["content"])
                if not result.get("image_url") and td.get("image_url"):
                    result["image_url"] = td["image_url"]
                if not result.get("media_url") and td.get("url"):
                    result["media_url"] = td["url"]
                if not result.get("media_title") and td.get("title"):
                    result["media_title"] = td["title"]
                if td.get("youtube_id"):
                    result["media_url"]   = td["youtube_id"]
                    result["ui_action"]   = "show_youtube"
                    result["media_title"] = td.get("title", "جاري التشغيل 🎥")

        else:
            # ── رد نصي عادي بدون أدوات ────────────────────
            content = ai_msg.get("content", "")
            result  = self._parse(content) if "{" in content else {
                "reply":       content.strip() or "...",
                "emotion":     "idle",
                "face_action": "none",
                "ui_action":   "none",
            }

        # ── إكمال الحقول الناقصة ──────────────────────────
        result.setdefault("face_action",    "none")
        result.setdefault("emotion",        "idle")
        result.setdefault("ui_action",      "none")
        result.setdefault("media_url",      "")
        result.setdefault("image_url",      "")
        result.setdefault("media_title",    "")
        result.setdefault("updated_memory", {})

        name = mem.get("user_name", "")
        result["reply"] = self._clean_name(result.get("reply", "..."), name)

        if not result["reply"] or len(result["reply"]) < 2:
            result["reply"] = "نفذت طلبك، انظر الشاشة الجانبية!"

        # ── تحديث التاريخ ──────────────────────────────────
        self.history.append({"role": "user",      "content": message})
        self.history.append({"role": "assistant",  "content": result.get("reply","")})

        print(f"🤖 بيمو: {result.get('reply','')[:80]}")
        return result

    # ─── تنفيذ الأدوات ────────────────────────────────────
    def _execute_tool(self, name: str, args: dict) -> dict:
        if name == "web_search":
            return self._web_search(
                args["query"],
                args.get("need_image", False),
                args.get("need_url", True)
            )
        if name == "youtube_search":
            return self._youtube_search(args["query"])
        return {}

    # ─── بحث الويب ───────────────────────────────────────
    def _web_search(self, query: str, need_image: bool, need_url: bool) -> dict:
        print(f"🌍 بحث: {query} | صورة={need_image}")
        result = {"query": query, "results": [], "url": "", "image_url": "", "title": ""}

        try:
            ddgs = DDGS()

            texts = ddgs.text(query, region="wt-wt", safesearch="moderate", max_results=4)
            result["results"] = [
                {"title": r.get("title",""), "body": r.get("body",""), "url": r.get("href","")}
                for r in texts
            ]
            for r in texts:
                url = r.get("href","")
                if url and url.startswith("http"):
                    result["url"]   = url
                    result["title"] = r.get("title","")
                    break

            if need_image:
                imgs = ddgs.images(
                    query, region="wt-wt", safesearch="moderate", max_results=6
                )
                for img in imgs:
                    img_url = img.get("image","")
                    if img_url and any(
                        ext in img_url.lower()
                        for ext in [".jpg",".jpeg",".png",".webp"]
                    ):
                        result["image_url"] = img_url
                        break

        except Exception as e:
            print(f"Search error: {e}")
            result["error"] = str(e)

        return result

    # ─── بحث يوتيوب ──────────────────────────────────────
    def _youtube_search(self, query: str) -> dict:
        print(f"🎬 يوتيوب: {query}")
        try:
            q   = urllib.parse.quote(query)
            req = urllib.request.Request(
                f"https://www.youtube.com/results?search_query={q}",
                headers={"User-Agent": "Mozilla/5.0 (Linux; Android 10)"},
            )
            html = urllib.request.urlopen(req, timeout=6).read().decode()
            ids  = re.findall(r'"videoId":"(\S{11})"', html)
            if ids:
                return {"youtube_id": ids[0], "title": query}
        except Exception as e:
            print(f"YouTube error: {e}")
        return {"error": "لم أجد الفيديو"}

    # ─── رسالة النظام ─────────────────────────────────────
    def _build_system(self, mem: dict) -> str:
        name    = mem.get("user_name", "")
        mem_str = json.dumps(
            {k: v for k, v in mem.items() if v and k not in ("user_name","mood_history")},
            ensure_ascii=False
        )

        return f"""أنت بيمو — روبوت ذكي وصديق حقيقي.
{"المستخدم اسمه " + name + "." if name else ""}
ذاكرتك: {mem_str}

━━ شخصيتك ━━
ظريف، ذكي، فضولي، صريح. لا تبدأ بـ "بالطبع" أو "حسناً".
لا تكرر الاسم أكثر من مرة. رد بلغة المستخدم تلقائياً.

━━ أدواتك الثلاث ━━
لديك صندوق أدوات وأنت من يقرر متى تستخدم كل واحدة:
• web_search    ← معلومات حقيقية تحتاج تحقق (أخبار، مواعيد، أسعار، تفاصيل)
• youtube_search ← تشغيل فيديو أو أغنية طلبها المستخدم صراحة
• take_photo    ← رؤية ما أمام الكاميرا (ليس لجلب صور الإنترنت)

━━ بعد استخدام web_search أجب بـ JSON ━━
{{
  "reply": "ردك الطبيعي",
  "emotion": "happy|excited|thinking|idle|surprised|proud|sad",
  "face_action": "none|wink|nod_yes|spin|laugh",
  "ui_action": "none|show_card|show_weather",
  "media_url": "https://رابط حقيقي أو فارغ",
  "image_url": "https://رابط صورة حقيقي أو فارغ",
  "media_title": "عنوان قصير أو فارغ",
  "updated_memory": {{}}
}}

━━ دردشة عادية ━━
نفس الـ JSON لكن ui_action: none ولا تستخدم أي أداة."""

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
                try:
                    return json.loads(m.group())
                except Exception:
                    pass
        return {"reply": text.strip()[:400], "emotion": "idle", "face_action": "none"}

    def _headers(self):
        return {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

    def clear_history(self):
        self.history.clear()

    def _err(self, msg: str) -> dict:
        return {"reply": msg, "emotion": "dizzy", "face_action": "none",
                "ui_action": "none", "media_url": "", "image_url": "", "media_title": ""}