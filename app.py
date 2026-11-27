import streamlit as st
import pandas as pd
import plotly.express as px
import json
import hashlib
from io import BytesIO
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import base64
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Pingr Analytics", page_icon="📊", layout="wide")

# Refresh on the two-hour archive cadence; manual refresh remains available in the sidebar.
st_autorefresh(interval=7200000, key="pingr_archive_auto_refresh")

st.markdown("""
<style>
:root{--bg:#05080f;--panel:#0b1627;--line:rgba(66,184,244,.20);--muted:#91a9c1;--text:#eef7ff;--cyan:#42b8f4;--blue:#168bd0;--ice:#91d7f5;--green:#55c7a5;--red:#f07888}
.stApp{background:radial-gradient(ellipse at 50% -12%,rgba(20,117,183,.18),transparent 42%),linear-gradient(180deg,#05080f 0%,#07111e 52%,#050a13 100%);color:var(--text)}
.stApp:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.09;background-image:linear-gradient(rgba(66,184,244,.07) 1px,transparent 1px),linear-gradient(90deg,rgba(66,184,244,.07) 1px,transparent 1px);background-size:52px 52px;mask-image:linear-gradient(to bottom,black,transparent 75%)}
.block-container{max-width:1480px;padding:1.1rem 2rem 3rem;position:relative}
[data-testid="stHeader"]{background:rgba(5,8,15,.82);backdrop-filter:blur(16px)}
[data-testid="stSidebar"],section[data-testid="stSidebar"]{display:none!important}
h1,h2,h3{letter-spacing:-.045em;color:var(--text)}
.pingr-hero{position:relative;overflow:hidden;display:flex;align-items:center;gap:28px;padding:28px 34px;border:1px solid rgba(66,184,244,.27);border-radius:22px;background:linear-gradient(112deg,rgba(7,20,36,.98),rgba(9,28,49,.96) 58%,rgba(9,19,38,.98));box-shadow:0 22px 60px rgba(0,0,0,.28),inset 0 1px 0 rgba(255,255,255,.045);margin:.2rem 0 1.1rem}
.pingr-hero:after{content:"";position:absolute;width:370px;height:370px;right:-115px;top:-225px;border-radius:50%;background:radial-gradient(circle,rgba(35,164,226,.18),rgba(17,91,151,.06) 48%,transparent 70%);pointer-events:none}
.pingr-brand{position:relative;z-index:1;display:flex;flex-direction:column;align-items:center;justify-content:center;min-width:150px}
.pingr-radar{width:72px;height:72px;border-radius:50%;position:relative;background:repeating-radial-gradient(circle,transparent 0 4px,rgba(48,174,239,.55) 4.7px 5.5px,transparent 6px 9px);filter:drop-shadow(0 0 8px rgba(43,174,240,.22))}
.pingr-radar:after{content:"";position:absolute;width:9px;height:9px;border-radius:50%;background:#42b8f4;left:50%;top:50%;transform:translate(-50%,-50%);box-shadow:0 0 10px #42b8f4}
.pingr-wordmark{font-size:2.65rem;line-height:1.05;font-weight:400;letter-spacing:-.07em;color:#42b8f4;text-shadow:0 2px 0 #176b9e}
.pingr-hero-copy{position:relative;z-index:1;min-width:0}
.pingr-eyebrow{color:#91d7f5;text-transform:uppercase;letter-spacing:.19em;font-size:.66rem;font-weight:850;margin:0 0 .55rem}
.pingr-title{font-size:clamp(1.75rem,3.4vw,2.65rem);font-weight:900;letter-spacing:-.075em;margin:0;color:#f3f8ff;line-height:1.05}
.pingr-title span{background:linear-gradient(100deg,#42b8f4,#91d7f5);-webkit-background-clip:text;background-clip:text;color:transparent}
.pingr-subtitle{color:#a9bfd4;font-size:.93rem;margin:.55rem 0 0}
.pingr-hero-meta{display:flex;gap:8px;flex-wrap:wrap;margin-top:15px}
.pingr-chip{display:inline-block;padding:6px 10px;border:1px solid rgba(66,184,244,.23);border-radius:999px;background:rgba(4,13,24,.58);color:#c7e4f6;font-size:.70rem;font-weight:750}
h2{font-size:1.2rem!important;margin:1rem 0 .7rem!important;font-weight:850!important}
h3{font-size:1rem!important;font-weight:800!important}
[data-testid="stMetric"]{background:linear-gradient(145deg,rgba(13,34,56,.96),rgba(8,20,35,.98));border:1px solid rgba(66,184,244,.22);border-radius:16px;padding:15px 17px;box-shadow:0 10px 28px rgba(0,0,0,.20),inset 0 1px 0 rgba(255,255,255,.04);min-height:100px}
[data-testid="stMetric"]:hover{border-color:rgba(66,184,244,.55);box-shadow:0 14px 32px rgba(0,0,0,.24),0 0 22px rgba(36,159,222,.08)}
[data-testid="stMetricLabel"]{color:#9ebbd2;font-size:.71rem;letter-spacing:.065em;text-transform:uppercase;font-weight:800}
[data-testid="stMetricValue"]{color:#f3f9ff;font-weight:900;font-size:1.75rem;letter-spacing:-.055em}
div[data-testid="stExpander"]{border:1px solid var(--line);border-radius:14px;background:rgba(9,22,38,.82);overflow:hidden}
.stButton button,.stDownloadButton button{border-radius:11px;border:1px solid rgba(66,184,244,.36);min-height:41px;background:linear-gradient(110deg,rgba(13,69,105,.9),rgba(12,43,76,.92));color:#f2f9ff;font-weight:800}
.stButton button:hover,.stDownloadButton button:hover{border-color:#91d7f5;box-shadow:0 0 20px rgba(66,184,244,.17);color:white}
[data-testid="stDataFrame"]{border:1px solid rgba(66,184,244,.18);border-radius:13px;overflow:hidden;background:rgba(7,17,30,.82)}
button[data-baseweb="tab"]{color:#9eb6cb!important;font-weight:800!important;padding:11px 14px!important;border:1px solid transparent!important;border-radius:10px 10px 0 0!important}
button[data-baseweb="tab"][aria-selected="true"]{color:#72cefa!important;background:rgba(22,112,165,.16)!important;border:1px solid rgba(66,184,244,.22)!important;border-bottom:2px solid #42b8f4!important}
[data-testid="stTabs"] [data-baseweb="tab-list"]{gap:5px;border-bottom:1px solid rgba(66,184,244,.17);margin-bottom:18px;flex-wrap:wrap}
[data-testid="stTabs"] [data-baseweb="tab-panel"]{padding-top:13px}
[data-testid="stPlotlyChart"]{border:1px solid rgba(66,184,244,.18);border-radius:16px;background:linear-gradient(145deg,rgba(10,26,44,.86),rgba(6,15,27,.82));padding:6px;box-shadow:0 10px 28px rgba(0,0,0,.14)}
[data-testid="stAlert"]{border-radius:13px}
hr{border-color:rgba(66,184,244,.16)!important}
.stCaption{color:#8fa9c1}
@media(max-width:900px){.block-container{padding:.8rem .9rem 1.7rem}.pingr-hero{padding:21px 20px;gap:20px}.pingr-brand{min-width:112px}.pingr-radar{width:58px;height:58px}.pingr-wordmark{font-size:2.15rem}[data-testid="stMetric"]{padding:11px 12px;min-height:86px}[data-testid="stMetricValue"]{font-size:1.35rem}}
@media(max-width:600px){.block-container{padding:.55rem .6rem 1.3rem}.pingr-hero{padding:17px 15px;gap:13px}.pingr-brand{min-width:78px}.pingr-radar{width:46px;height:46px}.pingr-wordmark{font-size:1.65rem}.pingr-title{font-size:1.65rem}.pingr-subtitle{font-size:.82rem}[data-testid="stMetricLabel"]{font-size:.64rem}[data-testid="stMetricValue"]{font-size:1.12rem}}
</style>
""", unsafe_allow_html=True)


class ArchiveUpload(BytesIO):
    def __init__(self, name, content):
        super().__init__(content)
        self.name = name

# Read the live archive directly from Cloudflare R2 through the read-only Worker API.
# The Worker decompresses .gz objects and returns JSONL; Streamlit does not need
# R2 or GitHub credentials.
R2_WORKER_URL = "https://binance-discord-alert.alisraja.workers.dev"
R2_INDEX_URL = f"{R2_WORKER_URL}/dashboard/index"
R2_FILE_URL = f"{R2_WORKER_URL}/dashboard/file"

@st.cache_data(ttl=60, show_spinner=False)
def r2_archive_index():
    # Current-day view only, using Pakistan local date.
    today = datetime.now(ZoneInfo("Asia/Karachi")).date()
    date_path = f"/{today:%Y/%m/%d}/"
    objects = []
    cursor = None
    seen_cursors = set()
    last_run = None
    while True:
        params = {"cursor": cursor} if cursor else {}
        response = requests.get(R2_INDEX_URL, params=params, timeout=(15, 60))
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok", False):
            raise RuntimeError(f"R2 index returned an error: {payload}")
        objects.extend(payload.get("objects", []))
        if last_run is None:
            last_run = payload.get("last_run")
        next_cursor = payload.get("cursor")
        if not next_cursor:
            break
        if next_cursor in seen_cursors:
            raise RuntimeError("R2 index pagination returned a repeated cursor; stopping to avoid an infinite loop.")
        seen_cursors.add(next_cursor)
        cursor = next_cursor

    # Keep only today's compressed log objects. Older R2 archives remain untouched.
    archives = [
        {
            "key": item["key"],
            "name": item["key"].rsplit("/", 1)[-1],
            "size": item.get("size", 0),
            "uploaded": item.get("uploaded")
        }
        for item in objects
        if item.get("key", "").lower().endswith(".gz")
        and date_path in f'/{item.get("key", "").lstrip("/")}'
    ]
    archives.sort(key=lambda item: (item.get("uploaded") or "", item["key"]))
    return archives, last_run

@st.cache_data(ttl=3600, max_entries=1500, show_spinner=False)
def r2_archive_file(key, size, uploaded):
    response = requests.get(
        R2_FILE_URL,
        params={"key": key},
        timeout=(15, 180)
    )
    response.raise_for_status()
    return response.content

def load_archive():
    objects, last_run = r2_archive_index()
    loaded, errors = [], []
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = {
            pool.submit(r2_archive_file, item["key"], item["size"], item.get("uploaded")): item
            for item in objects
        }
        for job in as_completed(jobs):
            item = jobs[job]
            try:
                content = job.result()
                if content:
                    loaded.append((item["name"], content))
            except Exception as exc:
                errors.append(f'{item["key"]}: {type(exc).__name__}: {exc}')

    loaded.sort(key=lambda item: item[0])
    latest = max((item.get("uploaded") or item["name"] for item in objects), default="Not available")
    return loaded, {
        "files": len(objects),
        "loaded": len(loaded),
        "errors": errors,
        "updated": latest,
        "last_sync": last_run,
        "objects": objects
    }

today_label = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%d %b %Y")
control_left, control_right = st.columns([1, 5])
with control_left:
    if st.button("↻  Refresh archive", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with control_right:
    st.markdown(
        f'<div style="padding:10px 14px;border:1px solid rgba(66,184,244,.18);border-radius:11px;background:rgba(8,24,40,.72);color:#a9c5da;font-size:.82rem">'
        f'<strong style="color:#72cefa">CLOUDFLARE R2</strong> &nbsp;·&nbsp; Today only: {today_label} PKT'
        f' &nbsp;·&nbsp; Auto-refresh every 2 hours &nbsp;·&nbsp; Bucket: pingr / pingr/logs/</div>',
        unsafe_allow_html=True
    )
try:
    with st.spinner("Reading Pingr snapshots directly from Cloudflare R2…"):
        archive_files, archive_status = load_archive()
except Exception as exc:
    st.error(f"Could not read the Cloudflare R2 archive: {type(exc).__name__}: {exc}")
    st.info("Check that the deployed archive Worker exposes /dashboard/index and /dashboard/file.")
    st.stop()
uploads = [ArchiveUpload(name, content) for name, content in archive_files]
status_cols = st.columns(3)
status_cols[0].metric("R2 objects loaded", f'{archive_status["loaded"]:,}')
status_cols[1].metric("Latest R2 object", archive_status["updated"])
status_cols[2].metric("Read errors", f'{len(archive_status["errors"]):,}')
if archive_status["last_sync"]:
    st.caption(f'Last GitHub mirror sync: {archive_status["last_sync"].get("completedAt", "status available")}')
if archive_status["errors"]:
    with st.expander(f'{len(archive_status["errors"])} R2 object(s) could not be read'):
        st.write(archive_status["errors"])
else:
    st.success("R2 archive read completed without file errors.")
st.caption("Individual archive files are cached by key, size and upload time.")


def parse_files(files):
    per_file, errors = {}, []
    all_records = []
    seen_global = set()
    duplicate_count = 0
    for f in files or []:
        rows, seen_file = [], set()
        raw_text = f.getvalue().decode("utf-8-sig", errors="replace")
        for line_no, line in enumerate(raw_text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    raise ValueError("JSON line is not an object")
                fingerprint = hashlib.sha256(
                    json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()
                ).hexdigest()
                if fingerprint in seen_file:
                    duplicate_count += 1
                    continue
                seen_file.add(fingerprint)
                item = dict(obj)
                item["_source_file"] = f.name
                item["_line"] = line_no
                rows.append(item)
                if fingerprint not in seen_global:
                    seen_global.add(fingerprint)
                    all_records.append(item)
                else:
                    duplicate_count += 1
            except Exception as exc:
                errors.append({"file": f.name, "line": line_no, "error": str(exc)})
        per_file[f.name] = rows
    return per_file, all_records, errors, duplicate_count


def make_df(rows):
    if not rows:
        return pd.DataFrame()
    return pd.json_normalize(rows, sep=".")


def ncol(df, name):
    if name not in df.columns:
        return pd.Series(index=df.index, dtype="float64")
    return pd.to_numeric(df[name], errors="coerce")


def metric_row(items):
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)


def prepare(rows):
    df = make_df(rows)
    if df.empty:
        return df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    if "event_type" not in df:
        df["event_type"] = "unknown"
    alerts = df[df.event_type.eq("alert_record")].copy()
    outcomes = df[df.event_type.eq("alert_outcome")].copy()
    generic = df[~df.event_type.isin(["alert_record", "alert_outcome"])].copy()
    for c in ["final_percent", "peak_percent", "worst_percent", "signal_score", "rsi_14", "rsi_6", "atr_pct", "vol_ratio", "btc_1h", "btc_4h", "pullback", "run24", "dist_ma20", "mfe_percent", "mae_percent", "pnl_percent", "volume_spike_5m", "volume_spike_15m"]:
        if c in alerts.columns:
            alerts[c] = pd.to_numeric(alerts[c], errors="coerce")
    if not alerts.empty:
        alerts["detector"] = alerts.get("detector", pd.Series("Unknown", index=alerts.index)).fillna("Unknown")
        alerts["symbol"] = alerts.get("symbol", pd.Series("Unknown", index=alerts.index)).fillna("Unknown")
    return df, alerts, outcomes, generic


def detector_summary(alerts):
    if alerts.empty or "final_percent" not in alerts:
        return pd.DataFrame()
    a = alerts.copy()
    a["final_percent"] = pd.to_numeric(a["final_percent"], errors="coerce")
    a = a.dropna(subset=["final_percent"])
    if a.empty:
        return pd.DataFrame()
    # Consistent descriptive outcome bands used by the upgraded dashboard:
    # win >= +1%, loss <= -0.5%, neutral between those thresholds.
    a["outcome_class"] = "neutral"
    a.loc[a["final_percent"] >= 1.0, "outcome_class"] = "win"
    a.loc[a["final_percent"] <= -0.5, "outcome_class"] = "loss"
    out = a.groupby("detector", dropna=False).agg(
        alerts=("final_percent", "size"),
        wins=("outcome_class", lambda x: int((x == "win").sum())),
        losses=("outcome_class", lambda x: int((x == "loss").sum())),
        neutral=("outcome_class", lambda x: int((x == "neutral").sum())),
        avg_return=("final_percent", "mean"),
        median_return=("final_percent", "median"),
        avg_peak=("peak_percent", "mean") if "peak_percent" in a.columns else ("final_percent", "mean"),
    ).reset_index()
    decisive = out.wins + out.losses
    out["win_rate"] = (out.wins / decisive.replace(0, pd.NA) * 100).fillna(0)
    return out


def latest_outcomes(outcomes):
    """Keep the latest timestamped evaluation per alert_id; never merge with alert_record."""
    if outcomes.empty or not {"alert_id", "result"}.issubset(outcomes.columns):
        return pd.DataFrame()
    out = outcomes.copy()
    if "timestamp" in out:
        out["_parsed_timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce", utc=True)
        out = out.sort_values("_parsed_timestamp")
    out = out.dropna(subset=["alert_id"]).drop_duplicates(subset=["alert_id"], keep="last")
    return out.drop(columns=["_parsed_timestamp"], errors="ignore")


def outcome_counts(frame):
    if frame.empty or "result" not in frame:
        return {"alerts": 0, "wins": 0, "losses": 0, "neutral": 0, "decisive_rate": float("nan")}
    result = frame["result"].astype(str).str.lower()
    wins, losses, neutral = int(result.eq("win").sum()), int(result.eq("loss").sum()), int(result.eq("neutral").sum())
    decisive = wins + losses
    return {"alerts": len(frame), "wins": wins, "losses": losses, "neutral": neutral,
            "decisive_rate": wins / decisive * 100 if decisive else float("nan")}


def render_outcome_intelligence(outcomes):
    """Analyses alert_outcome stream independently from detector alert_record rows."""
    st.markdown('<div class="pingr-eyebrow">05 / Signal intelligence</div>', unsafe_allow_html=True)
    st.header("Signal intelligence")
    latest = latest_outcomes(outcomes)
    if latest.empty:
        st.info("No usable alert_outcome records with alert IDs were found in these logs.")
        return

    for col in ["original_volume_5m", "original_price_change_5m", "original_rsi_15m",
                "original_score", "pnl_percent", "mfe_percent", "mae_percent"]:
        if col in latest:
            latest[col] = pd.to_numeric(latest[col], errors="coerce")

    c = outcome_counts(latest)
    metric_row([
        ("Unique evaluated alerts", f"{c['alerts']:,}"),
        ("Wins", f"{c['wins']:,}"),
        ("Losses", f"{c['losses']:,}"),
        ("Neutral", f"{c['neutral']:,}"),
        ("Decisive win rate", f"{c['decisive_rate']:.1f}%" if pd.notna(c["decisive_rate"]) else "—"),
    ])
    st.caption("Latest timestamped outcome per alert_id. Decisive win rate excludes neutral outcomes. This is a different stream from tracked detector records.")

    st.subheader("5-minute volume spike")
    if "original_volume_5m" in latest:
        bins = [
            ("<1.5×", lambda x: x < 1.5), ("1.5–3×", lambda x: 1.5 <= x < 3),
            ("3–5×", lambda x: 3 <= x < 5), ("5–10×", lambda x: 5 <= x < 10),
            (">10×", lambda x: x >= 10),
        ]
        rows = []
        for label, test in bins:
            group = latest[latest.original_volume_5m.notna() & latest.original_volume_5m.map(test)]
            stats = outcome_counts(group)
            rows.append({"Volume ratio": label, "Alerts": stats["alerts"], "Wins": stats["wins"],
                         "Losses": stats["losses"], "Neutral": stats["neutral"],
                         "Win rate · decisive": stats["decisive_rate"]})
        volume_table = pd.DataFrame(rows)
        st.dataframe(volume_table.style.format({"Win rate · decisive": "{:.1f}%"}), use_container_width=True, hide_index=True)
        high = latest[latest.original_volume_5m >= 5]
        low = latest[latest.original_volume_5m.notna() & (latest.original_volume_5m < 5)]
        hs, ls = outcome_counts(high), outcome_counts(low)
        st.info(
            f"Exploratory split: ≥5× has {hs['wins']} wins / {hs['losses']} losses / {hs['neutral']} neutral "
            f"({hs['decisive_rate']:.1f}% decisive win rate); below 5× has {ls['wins']} / {ls['losses']} / "
            f"{ls['neutral']} ({ls['decisive_rate']:.1f}%). Observational sample only—not a live filter recommendation."
        )
    else:
        st.info("The uploaded alert_outcome records do not contain original_volume_5m.")

    left, right = st.columns(2)
    with left:
        st.subheader("RSI 15m by outcome")
        if "original_rsi_15m" in latest:
            bands = [("<30", lambda x:x<30),("30–40",lambda x:30<=x<40),("40–50",lambda x:40<=x<50),
                     ("50–60",lambda x:50<=x<60),("60–70",lambda x:60<=x<70),("≥70",lambda x:x>=70)]
            rs=[]
            for label, fn in bands:
                g=latest[latest.original_rsi_15m.notna() & latest.original_rsi_15m.map(fn)]
                z=outcome_counts(g)
                rs.append({"RSI band":label,"Alerts":z["alerts"],"Wins":z["wins"],"Losses":z["losses"],
                           "Neutral":z["neutral"],"Decisive win %":z["decisive_rate"]})
            st.dataframe(pd.DataFrame(rs).style.format({"Decisive win %":"{:.1f}"}),use_container_width=True,hide_index=True)
        else:
            st.caption("RSI 15m is not present in this outcome stream.")
    with right:
        st.subheader("MACD by timeframe")
        macd_rows=[]
        for field,label in [("original_macd_5m","5m"),("original_macd_15m","15m"),("original_macd_1h","1h")]:
            if field not in latest: continue
            known=latest[latest[field].map(lambda x:isinstance(x,bool))]
            for bullish,group_label in [(True,"Bullish"),(False,"Not bullish")]:
                g=known[known[field].eq(bullish)]
                z=outcome_counts(g)
                macd_rows.append({"TF":label,"State":group_label,"Alerts":z["alerts"],"W/L/N":f"{z['wins']}/{z['losses']}/{z['neutral']}",
                                  "Decisive win %":z["decisive_rate"]})
        if macd_rows:
            st.dataframe(pd.DataFrame(macd_rows).style.format({"Decisive win %":"{:.1f}"}),use_container_width=True,hide_index=True)
        else:
            st.caption("MACD fields are not present in this outcome stream.")

    st.subheader("Score calibration")
    if "original_score" in latest:
        score_bands=[("≤8",lambda x:x<=8),("9–10",lambda x:9<=x<=10),("11–12",lambda x:11<=x<=12),
                     ("13–16",lambda x:13<=x<=16),("17+",lambda x:x>=17)]
        score_rows=[]
        for label,fn in score_bands:
            g=latest[latest.original_score.notna() & latest.original_score.map(fn)]
            z=outcome_counts(g)
            score_rows.append({"Score":label,"Alerts":z["alerts"],"Wins":z["wins"],"Losses":z["losses"],
                               "Neutral":z["neutral"],"Decisive win %":z["decisive_rate"]})
        st.dataframe(pd.DataFrame(score_rows).style.format({"Decisive win %":"{:.1f}"}),use_container_width=True,hide_index=True)
        st.caption("Score bands are descriptive. Small samples and overlapping signal conditions prevent causal conclusions.")

    st.subheader("Price movement and outcome")
    required={"original_price_change_5m","original_rsi_15m","original_volume_5m"}
    available=[x for x in ["original_price_change_5m","original_volume_5m","original_rsi_15m","pnl_percent","mfe_percent","mae_percent"] if x in latest]
    if available:
        summary=[]
        for result in ["win","loss","neutral"]:
            g=latest[latest.result.astype(str).str.lower().eq(result)]
            row={"Outcome":result.title(),"Alerts":len(g)}
            for field in available:
                row[field.replace("original_","").replace("_"," ")] = pd.to_numeric(g[field],errors="coerce").median()
            summary.append(row)
        st.dataframe(pd.DataFrame(summary).round(3),use_container_width=True,hide_index=True)
    st.caption("All comparisons use the latest logged evaluation per alert ID. They describe this sample and do not establish future predictive performance.")


def synopsis_observations(alerts, generic):
    notes = []
    perf = detector_summary(alerts)
    if not perf.empty:
        eligible = perf[perf.alerts >= 2]
        if not eligible.empty:
            best = eligible.sort_values("avg_return", ascending=False).iloc[0]
            worst = eligible.sort_values("avg_return").iloc[0]
            if best.detector == worst.detector:
                notes.append(("info", f"{best.detector} is the only detector with at least two closed alerts in this log."))
            else:
                notes.append(("good", f"{best.detector} had the strongest average return ({best.avg_return:+.2f}%)."))
                notes.append(("warn", f"{worst.detector} had the weakest average return ({worst.avg_return:+.2f}%)."))
    if not alerts.empty and {"peak_percent", "final_percent"}.issubset(alerts.columns):
        peak = pd.to_numeric(alerts.peak_percent, errors="coerce")
        final = pd.to_numeric(alerts.final_percent, errors="coerce")
        giveback = (peak >= 1) & (final < 0)
        count = int(giveback.sum())
        if count:
            notes.append(("warn", f"{count} alert(s) reached at least +1% peak but closed negative — review profit giveback."))
    mom = alerts[alerts.detector.eq("Momentum")].copy() if not alerts.empty else pd.DataFrame()
    if len(mom) >= 5 and "signal_score" in mom and "final_percent" in mom:
        scores = pd.to_numeric(mom.signal_score, errors="coerce")
        returns = pd.to_numeric(mom.final_percent, errors="coerce")
        valid = pd.DataFrame({"score": scores, "return": returns}).dropna()
        if len(valid) >= 5 and valid.score.nunique() > 1 and valid["return"].nunique() > 1:
            corr = valid.score.corr(valid["return"])
            if corr <= -0.35:
                notes.append(("warn", "Higher Momentum scores are not translating into better returns in this sample; monitor across more logs."))
            elif corr >= 0.35:
                notes.append(("good", "Momentum score and return move positively together in this sample; validate with more logs."))
            else:
                notes.append(("info", "No clear Momentum score/return relationship in this sample."))
    if generic.empty:
        notes.append(("info", "No generic scanner snapshots were present."))
    else:
        sent = generic.get("alert_sent", pd.Series(False, index=generic.index)).fillna(False).astype(bool).sum()
        notes.append(("info", f"Scanner recorded {len(generic)} snapshots, with {int(sent)} marked alert_sent."))
    return notes



if not uploads:
    st.warning("No readable JSONL log files were found in today’s R2 archive yet.")
    st.stop()

per_file, combined_rows, errors, duplicate_count = parse_files(uploads)
if not combined_rows:
    st.error("No valid JSON objects found. Check that each line contains one JSON object.")
    st.stop()

combined, alerts, outcomes, generic = prepare(combined_rows)
valid = alerts.dropna(subset=["final_percent"]).copy() if not alerts.empty and "final_percent" in alerts else pd.DataFrame()

# Parse timestamps once for reliable newest-first views.
if "timestamp" in combined.columns:
    combined["_ts"] = pd.to_datetime(combined["timestamp"], errors="coerce", utc=True)
else:
    combined["_ts"] = pd.NaT
if not alerts.empty and "timestamp" in alerts.columns:
    alerts["_ts"] = pd.to_datetime(alerts["timestamp"], errors="coerce", utc=True)
if not outcomes.empty and "timestamp" in outcomes.columns:
    outcomes["_ts"] = pd.to_datetime(outcomes["timestamp"], errors="coerce", utc=True)

# Latest archive file is determined from the timestamp embedded in its archive name.
latest_name = max(per_file.keys(), default=None)
latest_rows = per_file.get(latest_name, []) if latest_name else []
latest_df = make_df(latest_rows)
if not latest_df.empty and "timestamp" in latest_df:
    latest_df["_ts"] = pd.to_datetime(latest_df["timestamp"], errors="coerce", utc=True)
else:
    latest_df["_ts"] = pd.NaT
latest_time = latest_df["_ts"].max() if not latest_df.empty else pd.NaT
latest_time_pak = latest_time.tz_convert("Asia/Karachi").strftime("%d %b %Y · %I:%M:%S %p PKT") if pd.notna(latest_time) else "Timestamp unavailable"

today_hero_label = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%a · %d %b %Y")
st.markdown(
    f'<div class="pingr-hero">'
    f'<div class="pingr-brand"><div class="pingr-radar"></div><div class="pingr-wordmark">pingr</div></div>'
    f'<div class="pingr-hero-copy"><div class="pingr-eyebrow">Market intelligence workspace</div>'
    f'<div class="pingr-title">PINGR <span>ANALYTICS</span></div>'
    f'<div class="pingr-subtitle">Scanner performance · Signal quality · Coin intelligence</div>'
    f'<div class="pingr-hero-meta"><span class="pingr-chip">● R2 CONNECTED</span>'
    f'<span class="pingr-chip">▣ {today_hero_label} · PKT</span>'
    f'<span class="pingr-chip">↻ 2-HOUR ARCHIVE CYCLE</span></div></div></div>',
    unsafe_allow_html=True
)



# High-level navigation: keep the primary intelligence visible without a long continuous scroll.
tab_overview, tab_patterns, tab_scanner, tab_detectors, tab_coins, tab_quality, tab_logs = st.tabs([
    "Overview", "Patterns", "Scanner intelligence", "Detector performance", "Coin intelligence", "Signal quality", "Logs & diagnostics"
])

with tab_overview:
    # 1. Executive overview
    st.header("Executive overview")
    closed_count = len(valid)
    wins = int((valid["final_percent"] >= 1.0).sum()) if closed_count else 0
    losses = int((valid["final_percent"] <= -0.5).sum()) if closed_count else 0
    neutral = max(0, closed_count - wins - losses)
    decisive = wins + losses
    decisive_rate = wins / decisive * 100 if decisive else float("nan")
    avg_return = pd.to_numeric(valid["final_percent"], errors="coerce").mean() if closed_count else float("nan")
    latest_alert_time = alerts["_ts"].max() if not alerts.empty and "_ts" in alerts else pd.NaT
    latest_alert_label = (latest_alert_time.tz_convert("Asia/Karachi").strftime("%d %b · %I:%M %p PKT")
                          if pd.notna(latest_alert_time) else
                          ("Timestamp unavailable" if not alerts.empty else "No alert records"))
    metric_row([
        ("Closed tracked alerts", f"{closed_count:,}"),
        ("Wins / losses / neutral", f"{wins:,} / {losses:,} / {neutral:,}"),
        ("Decisive win rate", f"{decisive_rate:.1f}%" if decisive else "—"),
        ("Average final return", f"{avg_return:+.2f}%" if pd.notna(avg_return) else "—"),
    ])
    st.caption(f'Latest alert record: {latest_alert_label} · {len(combined):,} unique events across {archive_status["loaded"]:,} archived files · {duplicate_count:,} duplicate rows removed')

    # Winner vs loser intelligence from the dedicated outcome stream.
    st.subheader("Winners vs losers · what was different?")
    overview_outcomes = latest_outcomes(outcomes)
    # Shared pattern results feed both the compact Overview panel and the dedicated Patterns page.
    classified = pd.DataFrame()
    pattern_rows = []
    pattern_specs = []
    winner_n = 0
    loser_n = 0
    if not overview_outcomes.empty and {"symbol", "result"}.issubset(overview_outcomes.columns):
        overview_outcomes = overview_outcomes.copy()
        overview_outcomes["result"] = overview_outcomes["result"].astype(str).str.lower()
        for field in [
            "pnl_percent", "original_volume_5m", "original_price_change_5m",
            "original_rsi_15m", "original_score", "original_liquidity",
            "original_liquidity_usd", "original_quote_volume_24h",
            "original_volume_24h", "original_turnover_24h"
        ]:
            if field in overview_outcomes:
                overview_outcomes[field] = pd.to_numeric(overview_outcomes[field], errors="coerce")

        # Detect explicitly named liquidity/24h quote-volume fields; never relabel
        # a short-term volume ratio as liquidity.
        liquidity_fields = [
            col for col in overview_outcomes.columns
            if any(token in col.lower() for token in ("liquidity", "quote_volume", "turnover_24h", "volume_24h"))
            and pd.api.types.is_numeric_dtype(overview_outcomes[col])
        ]
        liquidity_field = next(
            (col for col in liquidity_fields if "original" in col.lower()),
            liquidity_fields[0] if liquidity_fields else None
        )
        indicator_fields = [
            ("original_score", "Signal score"),
            ("original_volume_5m", "5m volume ratio"),
            ("original_price_change_5m", "5m price change %"),
            ("original_rsi_15m", "15m RSI"),
        ]
        if liquidity_field:
            indicator_fields.append((liquidity_field, "Liquidity / 24h volume"))
        macd_fields = [
            (field, label) for field, label in [
                ("original_macd_5m", "MACD 5m"),
                ("original_macd_15m", "MACD 15m"),
                ("original_macd_1h", "MACD 1h")
            ] if field in overview_outcomes.columns
        ]

        classified = overview_outcomes[
            overview_outcomes["result"].isin(["win", "loss", "neutral"])
        ].copy()
        if not classified.empty:
            classified["symbol"] = classified["symbol"].fillna("Unknown").astype(str)
            if "pnl_percent" in classified:
                classified = classified.sort_values("pnl_percent", ascending=False, na_position="last")
            summary_rows = []
            for result_name, display_name in [("win", "Winners"), ("loss", "Losers"), ("neutral", "Neutral")]:
                group = classified[classified["result"].eq(result_name)]
                row = {"Group": display_name, "Alerts": len(group)}
                if "pnl_percent" in group:
                    row["Median P&L %"] = pd.to_numeric(group["pnl_percent"], errors="coerce").median()
                for field, label in indicator_fields:
                    if field in group:
                        row[label] = pd.to_numeric(group[field], errors="coerce").median()
                for field, label in macd_fields:
                    known = group[field].map(lambda value: isinstance(value, bool))
                    if known.any():
                        row[label + " bullish %"] = group.loc[known, field].astype(bool).mean() * 100
                summary_rows.append(row)
            summary_df = pd.DataFrame(summary_rows)
            def compact_volume(value):
                if pd.isna(value):
                    return "—"
                value = float(value)
                magnitude = abs(value)
                if magnitude >= 1_000_000_000:
                    return f"{value / 1_000_000_000:.2f}B"
                if magnitude >= 1_000_000:
                    return f"{value / 1_000_000:.1f}M"
                if magnitude >= 1_000:
                    return f"{value / 1_000:.1f}K"
                return f"{value:.0f}"

            # A stacked, colour-coded scorecard makes the three outcome groups
            # easier to scan without reintroducing a two-column dashboard layout.
            st.markdown("""
            <style>
            .outcome-card{border:1px solid rgba(66,184,244,.22);border-radius:16px;padding:15px 17px;margin:9px 0;background:linear-gradient(110deg,rgba(12,31,51,.96),rgba(7,18,32,.96));}
            .outcome-card.win{border-left:4px solid #55c7a5}
            .outcome-card.loss{border-left:4px solid #f07888}
            .outcome-card.neutral{border-left:4px solid #7893aa}
            .outcome-head{display:flex;align-items:center;gap:10px;margin-bottom:12px;color:#edf7ff;font-weight:850;font-size:1rem}
            .outcome-dot{width:9px;height:9px;border-radius:50%;display:inline-block}
            .outcome-metrics{display:flex;flex-wrap:wrap;gap:10px 24px}
            .outcome-metric{min-width:105px;flex:1}
            .outcome-label{font-size:.67rem;letter-spacing:.07em;text-transform:uppercase;color:#91a9c1;font-weight:750}
            .outcome-value{font-size:1.12rem;font-weight:850;color:#f3f9ff;margin-top:3px}
            </style>
            """, unsafe_allow_html=True)
            for _, card in summary_df.iterrows():
                group_name = str(card["Group"])
                css_group = {"Winners":"win","Losers":"loss","Neutral":"neutral"}.get(group_name,"neutral")
                dot_color = {"win":"#55c7a5","loss":"#f07888","neutral":"#7893aa"}[css_group]
                metrics_html = [("Alerts", f'{int(card["Alerts"]):,}')]
                for col in summary_df.columns:
                    if col in ("Group", "Alerts") or pd.isna(card[col]):
                        continue
                    value = card[col]
                    if col == "Liquidity / 24h volume":
                        shown = compact_volume(value)
                    elif col == "Median P&L %" or col.endswith("price change %"):
                        shown = f"{float(value):+.2f}%"
                    elif col.endswith("bullish %"):
                        shown = f"{float(value):.0f}%"
                    elif col == "15m RSI":
                        shown = f"{float(value):.1f}"
                    elif col in ("Signal score", "5m volume ratio"):
                        shown = f"{float(value):.2f}×" if col == "5m volume ratio" else f"{float(value):.1f}"
                    else:
                        shown = f"{float(value):.2f}"
                    metrics_html.append((col, shown))
                metric_markup = "".join(
                    f'<div class="outcome-metric"><div class="outcome-label">{label}</div><div class="outcome-value">{shown}</div></div>'
                    for label, shown in metrics_html
                )
                st.markdown(
                    f'<div class="outcome-card {css_group}"><div class="outcome-head"><span class="outcome-dot" style="background:{dot_color}"></span>{group_name}</div><div class="outcome-metrics">{metric_markup}</div></div>',
                    unsafe_allow_html=True
                )
            st.caption("Median indicator readings at alert time, grouped by the latest recorded outcome per alert ID. Volume is shown in compact K/M/B units. MACD figures show the share marked bullish. This is descriptive, not proof that an indicator caused the result.")

            symbol_cols = [col for col in [
                "symbol", "result", "pnl_percent", "original_score",
                "original_volume_5m", "original_rsi_15m", "original_price_change_5m"
            ] if col in classified]
            if liquidity_field and liquidity_field not in symbol_cols:
                symbol_cols.append(liquidity_field)
            if macd_fields:
                symbol_cols.extend(field for field, _ in macd_fields if field not in symbol_cols)
            symbol_view = classified[symbol_cols].copy()
            symbol_view = symbol_view.rename(columns={
                "symbol": "Symbol", "result": "Outcome", "pnl_percent": "P&L %",
                "original_score": "Signal score", "original_volume_5m": "5m volume",
                "original_rsi_15m": "15m RSI", "original_price_change_5m": "5m price change %",
            })
            if liquidity_field:
                symbol_view = symbol_view.rename(columns={liquidity_field: "Liquidity / 24h volume"})
            for field, label in macd_fields:
                symbol_view = symbol_view.rename(columns={field: label})
            winner_loser_tabs = st.tabs(["Winning symbols", "Losing symbols"])
            for pane, result_name in zip(winner_loser_tabs, ["win", "loss"]):
                with pane:
                    subset = symbol_view[classified["result"].eq(result_name)].head(15)
                    if subset.empty:
                        st.info(f"No {result_name} outcomes in the current archive.")
                    else:
                        table_format = {}
                        for col in subset.columns:
                            if col == "Liquidity / 24h volume":
                                table_format[col] = compact_volume
                            elif col == "P&L %" or col == "5m price change %":
                                table_format[col] = lambda value: "—" if pd.isna(value) else f"{float(value):+.2f}%"
                            elif col == "15m RSI":
                                table_format[col] = lambda value: "—" if pd.isna(value) else f"{float(value):.1f}"
                            elif col == "5m volume":
                                table_format[col] = lambda value: "—" if pd.isna(value) else f"{float(value):.2f}×"
                        st.dataframe(subset.style.format(table_format, na_rep="—"), use_container_width=True, hide_index=True)

            # Patterns are calculated from actual winner/loser outcomes in the
            # currently loaded archive. Use IQR (25th–75th percentile), not
            # min/max, so one outlier does not define a supposed winning range.
            st.divider()
            st.subheader("Patterns · winning conditions")
            st.caption("Observed middle 50% ranges for winners compared with losers. These are descriptive patterns, not trading rules.")
            pattern_specs = [
                ("original_rsi_15m", "15m RSI", "number"),
                ("original_volume_5m", "5m volume ratio", "multiple"),
                ("original_score", "Signal score", "number"),
                ("original_price_change_5m", "5m price change", "percent"),
            ]
            if liquidity_field:
                pattern_specs.insert(1, (liquidity_field, "24h liquidity / quote volume", "volume"))
            pattern_rows = []
            for field, label, kind in pattern_specs:
                if field not in classified.columns:
                    continue
                row = {"Pattern": label}
                for result_name, prefix in [("win", "Winners"), ("loss", "Losers")]:
                    values = pd.to_numeric(
                        classified.loc[classified["result"].eq(result_name), field],
                        errors="coerce"
                    ).dropna()
                    if values.empty:
                        row[prefix] = "No data"
                        continue
                    low, median, high = values.quantile([0.25, 0.50, 0.75]).tolist()
                    if kind == "volume":
                        row[prefix] = f"{compact_volume(low)}–{compact_volume(high)} (med {compact_volume(median)})"
                    elif kind == "percent":
                        row[prefix] = f"{low:+.2f}%–{high:+.2f}% (med {median:+.2f}%)"
                    elif kind == "multiple":
                        row[prefix] = f"{low:.2f}×–{high:.2f}× (med {median:.2f}×)"
                    else:
                        row[prefix] = f"{low:.1f}–{high:.1f} (med {median:.1f})"
                    row[prefix + " n"] = len(values)
                pattern_rows.append(row)

            if pattern_rows:
                winner_n = int(classified["result"].eq("win").sum())
                loser_n = int(classified["result"].eq("loss").sum())
                st.markdown("**Winner vs loser pattern snapshot**")
                pattern_view = pd.DataFrame(pattern_rows).rename(columns={
                    "Winners n": "Winner sample", "Losers n": "Loser sample"
                })
                st.dataframe(pattern_view, use_container_width=True, hide_index=True)
                st.caption(
                    f"Based on {winner_n} winning and {loser_n} losing evaluated alerts. "
                    "Ranges show the middle 50% with the median; open Patterns for the detailed read."
                )
                if min(winner_n, loser_n) < 5:
                    st.warning("Early read only: one or both outcome groups have fewer than five observations. Treat these patterns as descriptive, not trading thresholds.")
                else:
                    st.caption("Patterns are descriptive observations, not proof that an indicator caused an outcome.")
            else:
                st.info("No supported indicator fields are available to chart patterns yet.")
        else:
            st.info("No final win/loss/neutral outcomes are available yet.")
        if not liquidity_field:
            st.caption("Liquidity is not present as an explicit field in the current outcome records, so it is not estimated from volume ratios.")
    else:
        st.info("The current archive does not contain usable alert_outcome records with symbols and results. The comparison will populate when those records are available.")


    st.subheader("Outcome mix")
    if closed_count:
        outcome_mix = pd.DataFrame({"Outcome": ["Wins", "Losses", "Neutral"], "Alerts": [wins, losses, neutral]})
        outcome_fig = px.pie(outcome_mix, names="Outcome", values="Alerts", hole=.68,
                             color="Outcome", color_discrete_map={"Wins":"#55c7a5","Losses":"#f07888","Neutral":"#7893aa"})
        outcome_fig.update_traces(textinfo="percent", textposition="inside",
                                  marker=dict(line=dict(color="#07111e", width=3)),
                                  hovertemplate="%{label}: %{value}<extra></extra>")
        outcome_fig.update_layout(template="plotly_dark", height=340, showlegend=True,
                                  margin=dict(l=12,r=12,t=12,b=12), paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#eaf5ff"),
                                  legend=dict(orientation="h",y=-.06,x=.5,xanchor="center"))
        st.plotly_chart(outcome_fig,use_container_width=True,config={"displayModeBar":False})
    else:
        st.info("Outcome distribution will appear when closed alert records are available.")

    st.divider()
    st.subheader("Return snapshot")
    if closed_count:
        median_return = pd.to_numeric(valid["final_percent"], errors="coerce").median()
        best_return = pd.to_numeric(valid["final_percent"], errors="coerce").max()
        worst_return = pd.to_numeric(valid["final_percent"], errors="coerce").min()
        metric_row([
            ("Median final return", f"{median_return:+.2f}%" if pd.notna(median_return) else "—"),
            ("Best final return", f"{best_return:+.2f}%" if pd.notna(best_return) else "—"),
            ("Worst final return", f"{worst_return:+.2f}%" if pd.notna(worst_return) else "—"),
        ])
    else:
        st.info("Return summary will appear when closed tracked-alert records are available.")

with tab_patterns:
    st.header("Patterns · winning conditions")
    st.caption("Compare the middle 50% range and median for winning and losing alerts. These are observations from the current archive, not trading rules.")
    if pattern_rows:
        metric_row([
            ("Winning sample", f"{winner_n:,}"),
            ("Losing sample", f"{loser_n:,}"),
            ("Indicators compared", f"{len(pattern_rows):,}"),
        ])
        pattern_detail = pd.DataFrame(pattern_rows).rename(columns={
            "Winners n": "Winner sample", "Losers n": "Loser sample"
        })
        st.subheader("Indicator comparison")
        st.dataframe(pattern_detail, use_container_width=True, hide_index=True)
        st.subheader("How to read this")
        st.markdown(
            "- **Winners / Losers:** observed 25th–75th percentile ranges, with the median in parentheses.\n"
            "- **Sample counts:** number of non-missing observations used for each indicator and outcome group.\n"
            "- **No causal claim:** a difference in this sample does not prove that an indicator causes a better or worse result."
        )
        if min(winner_n, loser_n) < 5:
            st.warning(
                f"Small sample: {winner_n} winners and {loser_n} losers. "
                "The ranges may move substantially as more outcomes arrive; do not use them as hard filters."
            )
        else:
            st.success("Both outcome groups currently meet the five-observation minimum for an exploratory comparison; continue validating across more archive days.")
        if not liquidity_field:
            st.info("No explicit liquidity or 24h quote-volume field was found in these outcome records. The dashboard will not infer liquidity from short-term volume ratios.")
    else:
        st.info("No supported indicator comparisons are available yet. The page will populate when the archive contains usable alert_outcome records with indicator values and win/loss results.")

with tab_scanner:
    # 2. Scanner intelligence — report only fields and event types actually present in the logs.
    st.header("Scanner activity & diagnostics")
    unique_symbols = combined["symbol"].nunique() if "symbol" in combined.columns else 0
    alert_records = len(alerts)
    latest_eval_for_summary = latest_outcomes(outcomes)
    unique_evaluated = len(latest_eval_for_summary)
    other_log_events = len(generic)
    metric_row([
        ("Distinct symbols in logs", f"{unique_symbols:,}" if unique_symbols else "Not logged"),
        ("Other logged events", f"{other_log_events:,}"),
        ("Alert records", f"{alert_records:,}"),
        ("Unique evaluated alert IDs", f"{unique_evaluated:,}"),
    ])
    event_mix = generic.get("event_type", pd.Series(dtype="object")).fillna("unknown").astype(str).value_counts()
    st.subheader("Other event types in the logs")
    if not event_mix.empty:
        event_mix_df = event_mix.rename_axis("Event type").reset_index(name="Records")
        st.dataframe(event_mix_df, use_container_width=True, hide_index=True)
    else:
        st.info("No separate scanner/diagnostic event types were found in today's logs.")

    st.subheader("Recorded diagnostic stages and reasons")
    diagnostic_parts = []
    if "diagnostic.stage" in generic.columns:
        stages = generic["diagnostic.stage"].dropna().astype(str).value_counts()
        if not stages.empty:
            diagnostic_parts.append(stages.rename_axis("Stage").reset_index(name="Records"))
    if "diagnostic.reason" in generic.columns:
        reasons = generic["diagnostic.reason"].dropna().astype(str).value_counts().head(12)
        if not reasons.empty:
            diagnostic_parts.append(reasons.rename_axis("Reason").reset_index(name="Records"))
    if diagnostic_parts:
        for part in diagnostic_parts:
            st.dataframe(part, use_container_width=True, hide_index=True)
    else:
        st.info("Stage/rejection breakdown is not available in the current log fields. No funnel counts are inferred.")

    st.caption("These are log-derived counts, not a scanner funnel. Distinct symbols in the logs do not necessarily equal symbols scanned. A true scanned → qualified → rejected → alerted funnel requires explicit scanner-stage events.")

with tab_detectors:
    # 3. Detector performance
    st.header("Detector performance")
    perf_all = detector_summary(valid)
    if not perf_all.empty:
        show = perf_all[["detector", "alerts", "wins", "losses", "neutral", "win_rate", "avg_return", "median_return"]].copy()
        show["win_rate"] = show["win_rate"].map(lambda x: f"{x:.1f}%")
        show["avg_return"] = show["avg_return"].map(lambda x: f"{x:+.2f}%")
        show["median_return"] = show["median_return"].map(lambda x: f"{x:+.2f}%")
        show.columns = ["Detector", "Closed alerts", "Wins", "Losses", "Neutral", "Decisive win rate", "Avg return", "Median return"]
        st.dataframe(show, use_container_width=True, hide_index=True)
        chart = perf_all.sort_values("avg_return", ascending=True)
        fig = px.bar(chart, x="avg_return", y="detector", orientation="h",
                     text=chart["avg_return"].map(lambda x: f"{x:+.2f}%"),
                     color="avg_return", color_continuous_scale=["#f07888", "#315b7a", "#55c7a5"],
                     labels={"avg_return": "Average final return", "detector": ""})
        fig.update_layout(template="plotly_dark", height=max(220, 65 * len(chart)),
                          margin=dict(l=8, r=12, t=8, b=8), paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False,
                          font=dict(color="#edf5ff"))
        fig.update_traces(textposition="outside", cliponaxis=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No closed tracked-alert returns are available yet. Scanner skips and diagnostics are excluded from detector performance.")

with tab_coins:
    # 4. Coin intelligence
    st.header("Coin intelligence")
    coin_source = valid.copy() if not valid.empty and "symbol" in valid else pd.DataFrame()
    if not coin_source.empty:
        coin_source["final_percent"] = pd.to_numeric(coin_source["final_percent"], errors="coerce")
        coin_source = coin_source.dropna(subset=["symbol", "final_percent"])
        coin_rank = coin_source.groupby("symbol").agg(
            alerts=("final_percent", "size"),
            avg_return=("final_percent", "mean"),
            median_return=("final_percent", "median"),
            wins=("final_percent", lambda x: int((x >= 1.0).sum())),
            losses=("final_percent", lambda x: int((x <= -0.5).sum())),
            neutral=("final_percent", lambda x: int(((x > -0.5) & (x < 1.0)).sum())),
        ).reset_index()
        decisive_by_coin = coin_rank["wins"] + coin_rank["losses"]
        coin_rank["win_rate"] = (coin_rank["wins"] / decisive_by_coin.replace(0, pd.NA) * 100)
        coin_rank = coin_rank.sort_values(["avg_return", "alerts"], ascending=[False, False])
        display = coin_rank.rename(columns={
            "symbol": "Coin", "alerts": "Alerts", "wins": "Wins", "losses": "Losses",
            "neutral": "Neutral", "win_rate": "Decisive win rate",
            "avg_return": "Average return", "median_return": "Median return"
        }).copy()
        display["Decisive win rate"] = display["Decisive win rate"].map(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
        display["Average return"] = display["Average return"].map(lambda x: f"{x:+.2f}%")
        display["Median return"] = display["Median return"].map(lambda x: f"{x:+.2f}%")
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.caption("Closed tracked alerts only. Sample size is shown for every coin; small samples should not be treated as reliable rankings.")
    else:
        st.info("Coin rankings will appear when closed tracked-alert records include symbol and final return.")

with tab_quality:
    # 5. Signal quality — use the dedicated outcome stream, keeping it separate from alert_record.
    st.header("Signal quality")
    latest_eval = latest_outcomes(outcomes)
    if not latest_eval.empty:
        for col in ["original_volume_5m", "original_rsi_15m", "original_score", "pnl_percent", "mfe_percent", "mae_percent"]:
            if col in latest_eval:
                latest_eval[col] = pd.to_numeric(latest_eval[col], errors="coerce")
        counts = outcome_counts(latest_eval)
        metric_row([
            ("Evaluated alert IDs", f'{counts["alerts"]:,}'),
            ("Wins", f'{counts["wins"]:,}'),
            ("Losses", f'{counts["losses"]:,}'),
            ("Neutral", f'{counts["neutral"]:,}'),
            ("Decisive win rate", f'{counts["decisive_rate"]:.1f}%' if pd.notna(counts["decisive_rate"]) else "—"),
        ])
        quality_cols = [c for c in ["original_score", "original_volume_5m", "original_rsi_15m", "pnl_percent", "mfe_percent", "mae_percent"] if c in latest_eval]
        if quality_cols:
            display_cols = [c for c in ["symbol", "result"] + quality_cols if c in latest_eval]
            quality_view = latest_eval[display_cols].copy()
            quality_view = quality_view.rename(columns={
                "symbol": "Coin", "result": "Outcome", "original_score": "Original score",
                "original_volume_5m": "5m volume ratio", "original_rsi_15m": "15m RSI",
                "pnl_percent": "P&L", "mfe_percent": "Max favourable move", "mae_percent": "Max adverse move"
            })
            sort_col = "P&L" if "P&L" in quality_view.columns else None
            if sort_col:
                quality_view = quality_view.sort_values(sort_col, ascending=False, na_position="last")
            st.dataframe(quality_view, use_container_width=True, hide_index=True)
        st.caption("Latest evaluation per alert ID. Outcome records are analyzed separately and are not merged with detector alert records.")
    else:
        st.info("No usable alert_outcome records with alert IDs are present in the archive yet.")

with tab_logs:
    # 6. Latest R2 log — explicit latest file metadata and useful activity, not raw telemetry.
    st.header("Latest log file")
    if latest_name:
        st.markdown(f"**Newest file currently present in Cloudflare R2:** {latest_name}")
        if pd.notna(latest_time):
            archive_age_hours = (pd.Timestamp.now(tz="UTC") - latest_time).total_seconds() / 3600
            if archive_age_hours > 12:
                st.error(f"R2 ARCHIVE IS STALE · Newest archived event is {archive_age_hours:.1f} hours old. This is not proof that Pingr is currently logging or syncing.")
            else:
                st.success(f"R2 freshness: newest event is {archive_age_hours:.1f} hours old.")
        file_event_counts = latest_df.get("event_type", pd.Series(dtype="object")).fillna("unknown").value_counts()
        file_records = len(latest_rows)
        metric_row([
            ("Records in latest file", f"{file_records:,}"),
            ("Distinct symbols", f'{latest_df["symbol"].nunique() if "symbol" in latest_df else 0:,}'),
            ("Latest event time", latest_time_pak),
            ("File size", f'{next((x["size"] for x in archive_status["objects"] if x["name"] == latest_name), 0) / 1024:.1f} KB'),
        ])
        if not file_event_counts.empty:
            st.caption("Event mix: " + " · ".join(f"{k}: {v:,}" for k, v in file_event_counts.head(6).items()))
        if "diagnostic.reason" in latest_df:
            reasons = latest_df["diagnostic.reason"].dropna().astype(str).value_counts().head(5)
            if not reasons.empty:
                st.caption("Most common gate/skip reasons: " + " · ".join(f"{k} ({v})" for k, v in reasons.items()))
        if not latest_df.empty and "_ts" in latest_df:
            latest_activity = latest_df.sort_values("_ts", ascending=False, na_position="last")
            useful = latest_activity[
                ~latest_activity.get("event_type", pd.Series("", index=latest_activity.index)).astype(str).isin(
                    ["volume_cache_snapshot", "signal_quality_snapshot"]
                )
            ].head(12)
            cols = [c for c in ["timestamp", "symbol", "event_type", "alert_type", "signal_score", "final_percent", "diagnostic.stage", "diagnostic.reason"] if c in useful]
            if not useful.empty and cols:
                st.dataframe(useful[cols], use_container_width=True, hide_index=True)
            else:
                st.info("The newest file contains telemetry snapshots but no alert/rejection events to display.")
    else:
        st.info("No archive log file is available.")

    # Recent actual alerts, capped to 20 rows.
    st.header("Recent alerts")
    if not alerts.empty:
        recent = alerts.sort_values("_ts", ascending=False, na_position="last").head(20).copy()
        cols = [c for c in ["timestamp", "symbol", "detector", "alert_type", "signal_score", "final_percent", "peak_percent", "worst_percent", "exit_reason"] if c in recent]
        if cols:
            st.dataframe(recent[cols], use_container_width=True, hide_index=True)
        else:
            st.info("Alert records exist, but do not contain the expected display fields.")
    else:
        st.info("No alert_record events are present in the loaded archive.")

    # Keep raw detail available only when deliberately requested.
    with st.expander("Advanced diagnostics · raw data and exports"):
        st.caption("Open only when investigating a specific issue. This section is intentionally hidden by default.")
        st.write(f"Archive files loaded: {archive_status['loaded']:,} · Read errors: {len(archive_status['errors']):,} · Parse errors: {len(errors):,}")
        if errors:
            st.dataframe(pd.DataFrame(errors).head(100), use_container_width=True, hide_index=True)
        event_counts = combined.get("event_type", pd.Series("unknown", index=combined.index)).fillna("unknown").value_counts()
        st.dataframe(event_counts.rename_axis("Event type").reset_index(name="Records"), use_container_width=True, hide_index=True)
        csv_data = combined.drop(columns=["_ts"], errors="ignore").to_csv(index=False).encode("utf-8")
        st.download_button("Download all parsed records (CSV)", csv_data, "pingr_parsed_records.csv", "text/csv")
        jsonl_out = "\\n".join(json.dumps(r, default=str) for r in combined_rows)
        st.download_button("Download deduplicated records (JSONL)", jsonl_out, "pingr_deduplicated.jsonl", "application/json")

st.divider()
st.caption("PINGR ANALYTICS · Read-only analytics · R2 archive and Pingr engine are not modified by this dashboard.")
