# chat_agent.py — الفص الأول: بيمو يفكر بنفسه بدون سلاسل 🧠
# ✅ إصلاح مشكلة يوتيوب (تجاوز الحظر) + فرض عرض البطاقات بالقوة

import os, json, re, requests
from duckduckgo_search import DDGS

KEY   = os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY")
URL   = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

# ─── صندوق أدوات بيمو ─────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "ابحث في الإنترنت عن أي معلومة، أخبار، روابط تحميل (لعبة، فيلم، أنمي)، "
                "حالة طقس، أو صور."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "جملة البحث الدقيقة (مثال: تحميل لعبة جاتا سان اندرياس، أو مشاهدة انمي سولو ليفلنج)"
                    },
                    "need_image": {
                        "type": "boolean",
                        "description": "True إذا كان المستخدم يريد رؤية صورة للشيء"
                    },
                    "need_url": {
                        "type": "boolean",
                        "description": "True دائماً إذا سأل عن رابط تحميل أو مشاهدة"
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
            "description": "للبحث عن فيديو أو أغنية في يوتيوب لتشغيلها. استخدمها فوراً لو طلب فيديو أو موسيقى.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "اسم الفيديو أو الأغنية (مثال: مهارات كريستيانو رونالدو)"
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
            "description": "لالتقاط صورة بالكاميرا عندما يطلب المستخدم أن تنظر إليه أو تصف ما أمامك.",
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
                "temperature": 0.6,
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

            # توجيه صارم قبل الجولة الثانية ليتأكد من استخدام الروابط
            messages.append(ai_msg)
            messages += tool_results
            messages.append({
                "role": "system", 
                "content": "الآن اكتب الرد النهائي (JSON). إذا وفرت لك الأداة روابط (url) أو (youtube_id)، أخبر المستخدم أنك وجدتها وعرضتها على الشاشة. إياك أن تعتذر أو تقول 'لم أجد' إذا كان الرابط موجوداً في نتيجة الأداة!"
            })

            try:
                resp2 = requests.post(URL, headers=self._headers(), json={
                    "model":       MODEL,
                    "messages":    messages,
                    "max_tokens":  1024,
                    "temperature": 0.7,
                    "response_format": {"type": "json_object"},
                }, timeout=20)
                resp2.raise_for_status()
                ai_text = resp2.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"ChatAgent Round-2 error: {e}")
                return self._err("وجدت المعلومة لكن تعثرت في صياغة الرد.")

            result = self._parse(ai_text)

            # 🔥 حقن البيانات بالقوة لحماية بيمو من النسيان
            for tr in tool_results:
                td = json.loads(tr["content"])
                
                # إذا جاب بحث الويب رابط أو صورة
                if fn_name == "web_search":
                    if td.get("image_url"):
                        result["image_url"] = td["image_url"]
                        if result.get("ui_action") in ["none", "", None]:
                            result["ui_action"] = "show_card"
                    if td.get("url"):
                        result["media_url"] = td["url"]
                        if result.get("ui_action") in ["none", "", None]:
                            result["ui_action"] = "show_card"
                    if td.get("title") and not result.get("media_title"):
                        result["media_title"] = td["title"]

                # إذا جاب يوتيوب
                if fn_name == "youtube_search" and td.get("youtube_id"):
                    result["media_url"]   = td["youtube_id"]
                    result["ui_action"]   = "show_youtube"
                    result["media_title"] = td.get("title", "جاري التشغيل 🎥")
                    # إصلاح غباء الذكاء لو قال لم أجد رغم وجود الفيديو
                    if "لم أجد" in result.get("reply", "") or "لا أستطيع" in result.get("reply", ""):
                        result["reply"] = "لقد وجدت الفيديو يا بطل، تفضل مشاهدة ممتعة على الشاشة!"

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

    def _execute_tool(self, name: str, args: dict) -> dict:
        if name == "web_search":
            return self._web_search(
                args.get("query", ""),
                args.get("need_image", False),
                args.get("need_url", True)
            )
        if name == "youtube_search":
            return self._youtube_search(args.get("query", ""))
        return {}

    # ─── بحث الويب الذكي ───────────────────────────────────────
    def _web_search(self, query: str, need_image: bool, need_url: bool) -> dict:
        print(f"🌍 بحث: {query} | صورة={need_image}")
        result = {"query": query, "results": [], "url": "", "image_url": "", "title": ""}

        try:
            ddgs = DDGS()
            texts = ddgs.text(query, region="wt-wt", safesearch="moderate", max_results=4)
            result["results"] = [
                {"title": r.get("title",""), "body": r.get("body","")}
                for r in texts
            ]
            
            for r in texts:
                url = r.get("href","")
                if url and url.startswith("http"):
                    result["url"]   = url
                    result["title"] = r.get("title","")
                    break

            if need_image or "تحميل" in query or "انمي" in query:
                imgs = ddgs.images(query, region="wt-wt", safesearch="moderate", max_results=3)
                for img in imgs:
                    img_url = img.get("image","")
                    if img_url:
                        result["image_url"] = img_url
                        break

        except Exception as e:
            print(f"Search error: {e}")
            result["error"] = str(e)

        return result

    # ─── بحث يوتيوب المضاد للحظر ──────────────────────────────────────
    def _youtube_search(self, query: str) -> dict:
        print(f"🎬 يوتيوب (خطة تجاوز الحظر): {query}")
        try:
            ddgs = DDGS()
            # 💡 السر هنا: نبحث في محرك البحث الخارجي عن فيديوهات يوتيوب لتجنب حظر السيرفرات
            results = ddgs.text(f"site:youtube.com {query}", max_results=4)
            for r in results:
                url = r.get("href", "")
                if "watch?v=" in url:
                    vid = url.split("v=")[1].split("&")[0]
                    return {"youtube_id": vid, "title": r.get("title", query)}
            
            # خطة بديلة
            vids = ddgs.videos(query, max_results=3)
            for v in vids:
                url = v.get("content", "")
                if "watch?v=" in url:
                    vid = url.split("v=")[1].split("&")[0]
                    return {"youtube_id": vid, "title": v.get("title", query)}

        except Exception as e:
            print(f"YouTube error: {e}")
            return {"error": "حدث خطأ أثناء البحث في يوتيوب"}
            
        return {"error": "لم أجد الفيديو"}

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
تتحدث العربية المشكّلة بالحركات. 

━━ استخدام الأدوات ━━
إذا وفرت لك الأداة نتائج (روابط أو صور)، أخبر المستخدم أنك عرضتها له بجوارك، ولا تقل أبداً "لم أجد الرابط" إذا كانت الأداة قد أرجعته لك.

━━ بعد استخدام أي أداة أو للدردشة، أجب بـ JSON ━━
{{
  "reply": "ردك الطبيعي",
  "emotion": "happy|excited|thinking|idle|surprised|proud|sad",
  "face_action": "none|wink|nod_yes|spin|laugh",
  "ui_action": "none|show_card|show_weather|show_youtube",
  "media_url": "https://رابط حقيقي أو فارغ",
  "image_url": "https://رابط صورة حقيقي أو فارغ",
  "media_title": "عنوان قصير أو فارغ",
  "updated_memory": {{}}
}}"""

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
