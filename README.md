# Project Moohan — Launch Microsite (Pro)

Polished Flask site with animated gradient theme, dark/light toggle, timezone selector, multiple events, progress bar, curated live news (scraped), teaser audio, and optional admin route.

## Local
```bash
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:5000
```

## Deploy to Render
1. Push this folder to a GitHub repo.
2. In Render → **New → Blueprint**, point to your repo. It reads `render.yaml`.
3. (Optional) Set `ADMIN_TOKEN` in the Render service → Environment → Add Secret. Example: `ADMIN_TOKEN=changeme`.
4. Deploy. Health path: `/health`

### Admin Route
- URL: `/admin?token=YOUR_ADMIN_TOKEN`
- Paste JSON array of events to update. Example:
```json
[
  {"key":"teaser","name":"Teaser","iso_utc":"2025-09-20T01:00:00Z"},
  {"key":"reveal","name":"Main Reveal — Samsung Unpacked (Seoul)","iso_utc":"2025-09-29T01:00:00Z"},
  {"key":"sale_kr","name":"On-Sale (KR)","iso_utc":"2025-10-13T00:00:00Z"}
]
```

### News Feed
- Frontend calls `/api/news` which scrapes meta tags from trusted articles (no external API key required).
- Cached in memory for ~2 hours to be gentle to sources.
- If you want to add more sources, edit `NEWS_SOURCES` in `app.py`.

## Notes
- This is a fan page; dates/labels use rumored info by default. Update via `/admin` when official.
- Render free plan sleeps on inactivity; first request may be slower (“cold start”).