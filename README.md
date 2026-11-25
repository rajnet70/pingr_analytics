# Pingr Analytics Dashboard

Interactive Streamlit dashboard reading Pingr log archives directly from the private GitHub archive branch.

## Streamlit Community Cloud

- Repository: `rajnet70/pingr_analytics`
- Branch: `main`
- Main file: `app.py`

## Required Streamlit Secret

The dashboard reads files from the private repository `rajnet70/Binance-discord-alert`, branch `pingr-log-archive`.

Add a GitHub token as a Streamlit Community Cloud app secret (not as an in-app prompt):

```toml
GITHUB_TOKEN = "github_pat_..."
```

Use a fine-grained token with **Contents: Read-only** access to `rajnet70/Binance-discord-alert`. The token is used only by the Streamlit server to read the archive. It is not displayed in the dashboard or sent to visitors.

The app refreshes the GitHub archive index every 60 seconds and caches individual archive files by Git blob SHA.
