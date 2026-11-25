# Pingr Analytics Dashboard

Interactive Streamlit dashboard reading live Pingr log archives directly from Cloudflare R2.

## Streamlit Community Cloud

- Repository: `rajnet70/pingr_analytics`
- Branch: `main`
- Main file: `app.py`

No GitHub token or Streamlit secret is required. The app reads through the read-only dashboard endpoints on the Pingr archive Worker.

**Visibility note:** the dashboard API serves the archived JSONL files without authentication so the public Streamlit app can read them. Anyone who knows the Worker endpoint can retrieve those archived logs. Keep this endpoint public only if the archive contents are intended to be public.
