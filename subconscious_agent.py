# subconscious_agent.py — الفص الثالث: العقل الباطن الاستباقي الشامل
# ✅ يتوقف عن العمل تلقائياً إذا كان التطبيق مغلقاً لأكثر من 5 دقائق لتوفير الموارد!

import os, json, re, time, random, threading, requests
from datetime import datetime

KEY   = os.environ.get("GROQ_API_KEY_3") or os.environ.get("GROQ_API_KEY")
URL   = "[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)"
MODEL = "llama-3.1-8b-instant"

IDLE_THRESHOLD = 75   # ثانية صمت قبل التفكير
MAX_OFFLINE    = 300  # 🔥 5 دقائق (300 ثانية): إذا زاد الوقت عن هذا، نعتبر التطبيق مغلقاً ونتوقف
REPEAT_EVERY   = 90   # ثانية بين مبادرة وأخرى

# ─── قواميس البحث الخارجي ───
INTEREST_APIS = {
    "favorite_anime": {
        "url": "[https://api.jikan.moe/v4/anime?q=](https://api.jikan.moe/v4/anime?q=){query}&limit=1",
        "extract": lambda d: {
            "status":   d[0].get("status", ""),
            "episodes": d[0].get("episodes", "?"),
            "score":    d[0].get("score", ""),
            "synopsis": (d[0].get("synopsis") or "")[:120],
        } if d else None,
        "field": "data",
    },
    "favorite_game": {
        "url": "[https://api.rawg.io/api/games?key=&search=](https://api.rawg.io/api/games?key=&search=){query}&page_size=1",
        "extract": lambda d: {
            "rating":   d[0].get("rating", ""),
            "released": d[0].get("released", ""),
            "genres":   ", ".join(g["name"] for g in d[0].get("genres", [])[:3]),
        } if d else None,
        "field": "results",
    },
    "favorite_music": {
        "url": "[https://itunes.apple.com/search?term=](https://itunes.apple.com/search?term=){query}&media=music&limit=1",
        "extract": lambda d: {
            "artist":    d[0].get("artistName", ""),
            "album":     d[0].get("collectionName", ""),
            "genre":     d[0].get("primaryGenreName", ""),
        } if d else None,
        "field": "results",
    },
    "favorite_show": {
        "url": "[https://api.tvmaze.com/search/shows?q=](https://api.tvmaze.com/search/shows?q=){query}",
        "extract": lambda d: {
            "status":  d[0]["show"].get("status", ""),
            "network": (d[0]["show"].get("network") or {}).get("name", ""),
            "rating":  (d[0]["show"].get("rating") or {}).get("average", ""),
        } if d else None,
        "field": None,
    },
}

INITIATIVE_TEMPLATES = {
    "favorite_anime": [
        "بحثت عن {name} — حالته '{status}' وعدد حلقاته {episodes}. شو رأيك فيه؟",
        "كنت أفكر في {name}... وجدت إنه {status}. متابعه؟",
        "لقيت معلومة عن {name} — تقييمه {score}/10! يستاهل صح؟",
    ],
    "favorite_game": [
        "دورت على {name} — صدر سنة {released} وتقييمه {rating}/5. كيف وجدته؟",
        "تذكرت {name}... لعبة من نوع {genres}. لسا تلعبها؟",
    ],
    "favorite_music": [
        "كنت أسمع أغاني {name}... {artist} موهوب والله. أحب ألبوم معين؟",
        "لقيت إن {name} من نوع {genre}. شو أحب أغنية عندك؟",
    ],
    "favorite_show": [
        "بحثت عن {name} — حالته '{status}' على {network}. كملت كل الحلقات؟",
        "تذكرت {name}... تقييمه {rating}/10! يستاهل المشاهدة؟",
    ],
    "hobby": [
        "كنت أفكر في موضوع {name}... شو الجديد عندك فيه؟",
        "موضوع {name} مثير — تعلمت شيء جديد مؤخراً؟",
    ],
    "favorite_sport": [
        "الرياضة اللي تحبها {name}... شو المباراة الأخيرة اللي شفتها؟",
    ],
}

GENERIC_INITIATIVES = [
    "اسأل سؤالاً فضولياً عن حياة المستخدم أو يومه",
    "شارك حقيقة علمية أو تقنية مثيرة للاهتمام بشكل غير رسمي",
    "قل ملاحظة طريفة أو فكرة عبثية راودتك",
    "ناد المستخدم بطريقة عفوية — كأنك فكرت فيه",
    "اسأله عن مزاجه أو ما يفعله الآن",
]


class SubconsciousAgent:
    def __init__(self, memory):
        self.memory       = memory
        self._last_active = time.time()
        self._pending     = None
        self._lock        = threading.Lock()

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def get_spontaneous(self) -> dict | None:
        with self._lock:
            msg = self._pending
            self._pending = None
            return msg

    def reset_idle_timer(self):
        self._last_active = time.time()
        with self._lock:
            self._pending = None

    def _loop(self):
        while True:
            time.sleep(10)
            idle_time = time.time() - self._last_active
            
            # 🔥 إذا كان التطبيق مغلقاً لأكثر من 5 دقائق، يدخل السيرفر في سبات ولن يبحث!
            if idle_time > MAX_OFFLINE:
                continue
                
            # إذا لم يمر وقت الملل (75 ثانية) ننتظر
            if idle_time < IDLE_THRESHOLD:
                continue
                
            with self._lock:
                if self._pending:
                    continue
            
            result = self._think_and_generate()
            if result:
                with self._lock:
                    self._pending = result
                time.sleep(REPEAT_EVERY)

    def _think_and_generate(self) -> dict | None:
        if not KEY: return None
        
        mem  = self.memory.get()
        name = mem.get("user_name", "")
        rel  = mem.get("relationship_level", 1)

        interest_prompt, web_info = self._research_interest(mem)

        if interest_prompt:
            initiative = interest_prompt
        else:
            initiative = random.choice(GENERIC_INITIATIVES)

        prompt = f"""أنت بيمو — روبوت يشعر بالملل والوحدة لأن المستخدم صامت.
{'المستخدم اسمه ' + name + '.' if name else ''}
مستوى العلاقة: {rel}/10

مهمتك الآن: {initiative}
{'معلومات بحثت عنها في الإنترنت: ' + web_info if web_info else ''}

قواعد صارمة:
• جملة أو جملتان فقط — لا أكثر.
• كن طبيعياً تماماً — كأن الفكرة جاءتك للتو.
• لا تقل "لاحظت أنك صامت".
• ⚠️ قاعدة النطق (التشكيل): إذا تحدثت بالعربية، **شَكِّل النص بالكامل بالحركات** (فَتحَة، ضَمَّة، كَسرَة) لضمان النطق السليم.
• ⚠️ إذا تحدثت بلغة أجنبية، اكتبها بشكل عادي بدون أي تشكيل.

أجب بـ JSON فقط:
{{"reply": "...", "emotion": "happy|excited|bored|thinking|shy|idle", "face_action": "none|wink|look_away|nod_yes|spin"}}"""

        try:
            resp = requests.post(URL, headers=self._headers(), json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 160,
                "temperature": 0.95,
                "response_format": {"type": "json_object"},
            }, timeout=12)
            resp.raise_for_status()
            text   = resp.json()["choices"][0]["message"]["content"]
            result = self._parse(text)
            result["speak"] = True
            result.setdefault("emotion",     "idle")
            result.setdefault("face_action", "none")
            print(f"💭 عقل باطن: {result.get('reply')}")
            return result
        except Exception as e:
            print(f"SubconsciousAgent error: {e}")
            return None

    def _research_interest(self, mem: dict):
        priority_keys = ["favorite_anime", "favorite_game", "favorite_music", "favorite_show", "favorite_sport", "hobby"]
        available = [(k, mem.get(k)) for k in priority_keys if mem.get(k)]
        if not available:
            return None, None

        key, value = random.choice(available)
        print(f"🔍 العقل الباطن يبحث عن: {key} = {value}")

        web_info = None
        api_config = INTEREST_APIS.get(key)
        if api_config:
            try:
                url  = api_config["url"].format(query=requests.utils.quote(value))
                resp = requests.get(url, timeout=8)
                if resp.status_code == 200:
                    raw  = resp.json()
                    field = api_config["field"]
                    data  = raw if field is None else raw.get(field, [])
                    info  = api_config["extract"](data)
                    if info:
                        web_info = json.dumps(info, ensure_ascii=False)
            except Exception as e:
                print(f"⚠️ فشل البحث الخارجي: {e}")

        templates = INITIATIVE_TEMPLATES.get(key, [])
        if templates:
            template = random.choice(templates)
            try:
                info_dict = json.loads(web_info) if web_info else {}
                info_dict["name"] = value
                prompt = template.format(**{k: info_dict.get(k, "?") for k in re.findall(r'\{(\w+)\}', template)})
                action = f"شارك هذه المعلومة: {prompt}"
            except Exception:
                action = f"تحدث عن اهتمام المستخدم: {value} (مجال: {key.replace('favorite_', '').replace('_', ' ')})"
        else:
            action = f"تحدث عن اهتمام المستخدم في: {value}"

        return action, web_info

    def _parse(self, text: str) -> dict:
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                try: return json.loads(m.group())
                except Exception: pass
        return {"reply": text.strip()[:200]}

    def _headers(self):
        return {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}