from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from datetime import datetime, timezone
import os, json, time
from typing import List, Dict

# Optional scraping libs for news (Render will install these via requirements.txt)
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), 'data.json')
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")

# ---- Default events (UTC). These can be edited via /admin if ADMIN_TOKEN is set. ----
DEFAULT_EVENTS = [
    {
        "key": "teaser",
        "name": "Teaser Drop (rumored)",
        "iso_utc": "2025-09-20T01:00:00Z"
    },
    {
        "key": "reveal",
        "name": "Main Reveal — Samsung Unpacked (Seoul)",
        "iso_utc": "2025-09-29T01:00:00Z"  # 10:00 KST = 01:00 UTC
    },
    {
        "key": "sale_kr",
        "name": "On-Sale (KR, rumored)",
        "iso_utc": "2025-10-13T00:00:00Z"
    }
]

def _load_data() -> Dict:
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"events": DEFAULT_EVENTS}

def _save_data(data: Dict) -> None:
    try:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

STORE = _load_data()

@app.route("/")
def index():
    events = STORE.get("events", DEFAULT_EVENTS)
    # Ensure datetimes are valid ISO strings
    return render_template("index.html", events=events)

# ---- Admin: update events (requires ADMIN_TOKEN env var) ----
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not ADMIN_TOKEN:
        abort(404)
    token = request.args.get("token", "") or request.form.get("token", "")
    if token != ADMIN_TOKEN:
        return abort(403)
    if request.method == "POST":
        # Expect a JSON payload from form textarea
        raw = request.form.get("events_json", "").strip()
        try:
            data = json.loads(raw)
            if not isinstance(data, list):
                raise ValueError("events_json must be a JSON array")
            # Basic sanity check for keys
            for e in data:
                if not all(k in e for k in ("key", "name", "iso_utc")):
                    raise ValueError("Each event must have 'key', 'name', 'iso_utc'")
            STORE["events"] = data
            _save_data(STORE)
            return redirect(url_for("admin", token=token))
        except Exception as e:
            return render_template("admin.html", events=STORE["events"], error=str(e), token=token)
    return render_template("admin.html", events=STORE["events"], error=None, token=request.args.get("token",""))

# ---- Simple in-memory cache for news ----
_NEWS_CACHE = {"ts": 0, "data": []}
_NEWS_TTL = 60 * 60 * 2  # 2 hours

NEWS_SOURCES = [
    {
        "name": "Android Central",
        "url": "https://www.androidcentral.com/phones/samsung-galaxy/samsung-trifolding-phone-might-debut-as-soon-as-this-month"
    },
    {
        "name": "Tom's Guide",
        "url": "https://www.tomsguide.com/phones/samsung-phones/forget-the-iphone-17-samsung-tipped-to-reveal-a-trifold-phone-and-ai-glasses-later-this-month"
    },
    {
        "name": "TechRadar",
        "url": "https://www.techradar.com/computing/virtual-reality-augmented-reality/samsung-could-be-lining-up-a-third-unpacked-event-this-year-these-are-the-3-exciting-devices-that-could-make-an-appearance"
    },
    {
        "name": "XR Today",
        "url": "https://www.xrtoday.com/virtual-reality/save-the-date-samsung-xr-headset-project-moohan-could-launch-on-september-29-at-a-much-cheaper-price-than-the-apple-vision-pro/"
    },
    {
        "name": "9to5Google",
        "url": "https://9to5google.com/2025/09/02/samsung-might-unveil-galaxy-z-trifold-project-moohan-headset-later-this-month/"
    }
]

def _scrape_meta(url: str) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, timeout=10, headers=headers)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        def meta(prop, attr="property"):
            tag = soup.find("meta", {attr: prop})
            return tag["content"].strip() if tag and tag.get("content") else None

        title = meta("og:title") or (soup.title.text.strip() if soup.title else None)
        desc = meta("og:description") or meta("description", "name")
        image = meta("og:image")
        published = meta("article:published_time") or meta("og:updated_time") or meta("date", "name")
        if published and len(published) > 32:
            published = published[:32]
        return {
            "title": title or "Untitled",
            "summary": (desc or "")[:280],
            "image": image,
            "url": url,
            "source": url.split("/")[2],
            "published": published
        }
    except Exception:
        return {"title": "Unable to load", "summary": "", "image": None, "url": url, "source": url.split("/")[2], "published": None}

@app.route("/api/news")
def api_news():
    now = time.time()
    if now - _NEWS_CACHE["ts"] < _NEWS_TTL and _NEWS_CACHE["data"]:
        return jsonify({"items": _NEWS_CACHE["data"], "cached": True})
    items = []
    for s in NEWS_SOURCES:
        items.append(_scrape_meta(s["url"]))
    # Keep top 5
    items = [i for i in items if i.get("title") and i["title"] != "Unable to load"] or items
    items = items[:5]
    _NEWS_CACHE["data"] = items
    _NEWS_CACHE["ts"] = now
    return jsonify({"items": items, "cached": False})

@app.route("/health")
def health():
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)