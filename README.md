# Pingr Analytics Dashboard

Interactive Streamlit dashboard reading Pingr log archives directly from Cloudflare R2 through the read-only archive Worker API.

## Streamlit Community Cloud

- Repository: `rajnet70/pingr_analytics`
- Branch: `main`
- Main file: `app.py`

## Data source

The dashboard reads the paginated archive index from:

- `/dashboard/index`
- `/dashboard/file`

It retrieves compressed JSONL archives from the existing date-based folders under `pingr/logs/` in Cloudflare R2. All available date folders are included; the dashboard does not restrict ingestion to the current date.

The Worker decompresses each `.gz` object and returns JSONL. The dashboard uses the Worker read-only endpoints and does not write to R2.

No GitHub archive token or GitHub archive branch is used as a dashboard data source.

## Refresh

- Archive index cache: 60 seconds
- Automatic dashboard refresh: every 2 hours
- Manual refresh: available in the dashboard
