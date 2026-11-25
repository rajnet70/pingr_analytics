# Pingr Analytics Dashboard

Interactive Streamlit dashboard for Pingr archive analytics.

## Deploy on Streamlit Community Cloud

- Repository: `rajnet70/pingr_analytics`
- Branch: `main`
- Main file: `app.py`

In Streamlit Community Cloud, open the app settings and add this secret:

```toml
GITHUB_TOKEN = "YOUR_READ_ONLY_GITHUB_TOKEN"
```

The token must have read-only Contents access to the private repository `rajnet70/Binance-discord-alert`. Do not commit the token to this repository or share it in chat.

The dashboard reads archived data from the private `pingr-log-archive` branch. The dashboard app itself is public, so any analytics displayed in it can be seen by anyone with access to the public app URL.
