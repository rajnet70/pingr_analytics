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
:root{--bg:#070b14;--panel:#101b2c;--line:rgba(133,170,210,.18);--muted:#9aabc1;--text:#f3f7ff;--cyan:#35d9f5;--lime:#b7f36b;--violet:#9b8cff;--green:#42e0a5;--red:#ff718d}
.stApp{background:radial-gradient(ellipse at 8% -5%,rgba(22,191,220,.20),transparent 32%),radial-gradient(ellipse at 96% 0%,rgba(117,92,255,.18),transparent 30%),linear-gradient(180deg,#080e1a 0%,#070b14 55%,#090f1c 100%);color:var(--text)}
.stApp:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.16;background-image:linear-gradient(rgba(145,170,205,.07) 1px,transparent 1px),linear-gradient(90deg,rgba(145,170,205,.07) 1px,transparent 1px);background-size:42px 42px;mask-image:linear-gradient(to bottom,black,transparent 78%)}
.block-container{max-width:1680px;padding:1.25rem 1.6rem 3rem;position:relative}
[data-testid="stHeader"]{background:rgba(7,11,20,.72);backdrop-filter:blur(14px)}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0b1627,#080f1b);border-right:1px solid var(--line)}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{color:var(--text)}
h1,h2,h3{letter-spacing:-.04em;color:var(--text)}
.pingr-title{font-size:clamp(2rem,4vw,3.25rem);font-weight:900;letter-spacing:-.075em;margin:.1rem 0 .2rem;color:#f7fbff;text-shadow:0 5px 30px rgba(40,210,245,.12)}
.pingr-title span{background:linear-gradient(100deg,var(--cyan),#91a5ff 60%,var(--lime));-webkit-background-clip:text;background-clip:text;color:transparent}
.pingr-eyebrow{color:var(--lime);text-transform:uppercase;letter-spacing:.22em;font-size:.67rem;font-weight:900;margin-top:.5rem}
.pingr-subtitle{color:#a8b8ce;font-size:.93rem;margin:.3rem 0 .85rem;letter-spacing:.01em}
.pingr-rule{height:2px;background:linear-gradient(90deg,var(--cyan),rgba(155,140,255,.65),rgba(183,243,107,0));margin:.9rem 0 1.4rem;border-radius:8px;box-shadow:0 0 22px rgba(53,217,245,.18)}
h2{font-size:1.28rem!important;margin:1.1rem 0 .7rem!important;font-weight:800!important}
h3{font-size:1.02rem!important;font-weight:750!important}
[data-testid="stMetric"]{background:linear-gradient(145deg,rgba(19,36,58,.96),rgba(12,23,39,.98));border:1px solid rgba(113,163,204,.23);border-radius:17px;padding:15px 17px;box-shadow:0 12px 34px rgba(0,0,0,.22),inset 0 1px 0 rgba(255,255,255,.035);min-height:102px;transition:transform .18s ease,border-color .18s ease}
[data-testid="stMetric"]:hover{transform:translateY(-2px);border-color:rgba(53,217,245,.55)}
[data-testid="stMetricLabel"]{color:#a8bbd2;font-size:.76rem;letter-spacing:.055em;text-transform:uppercase;font-weight:750}
[data-testid="stMetricValue"]{color:#f4f8ff;font-weight:850;font-size:1.75rem;letter-spacing:-.055em}
[data-testid="stMetricDelta"]{font-size:.76rem}
div[data-testid="stExpander"]{border:1px solid var(--line);border-radius:15px;background:rgba(13,25,42,.78);overflow:hidden}
.stButton button,.stDownloadButton button{border-radius:11px;border:1px solid rgba(53,217,245,.32);min-height:42px;background:linear-gradient(110deg,rgba(25,71,94,.72),rgba(42,42,87,.72));color:#f3f8ff;font-weight:750;transition:all .18s ease}
.stButton button:hover,.stDownloadButton button:hover{border-color:var(--cyan);box-shadow:0 0 22px rgba(53,217,245,.16);color:white}
[data-testid="stDataFrame"]{border:1px solid rgba(133,170,210,.2);border-radius:13px;overflow:hidden;background:rgba(11,20,34,.72)}
button[data-baseweb="tab"]{color:#a8bbd2!important;font-weight:750!important;padding:12px 16px!important}
button[data-baseweb="tab"][aria-selected="true"]{color:#35d9f5!important;border-bottom:2px solid #35d9f5!important}
[data-testid="stTabs"] [data-baseweb="tab-list"]{gap:5px;border-bottom:1px solid rgba(133,170,210,.18);margin-bottom:18px;flex-wrap:wrap}
[data-testid="stTabs"] [data-baseweb="tab-panel"]{padding-top:12px}
[data-testid="stPlotlyChart"]{border:1px solid rgba(130,160,190,.16);border-radius:15px;background:rgba(10,22,37,.52);padding:5px}
[data-testid="stAlert"]{border-radius:13px}
hr{border-color:rgba(133,170,210,.16)!important}
.stCaption{color:#91a4bb}
@media(max-width:900px){.block-container{padding:.8rem .8rem 1.7rem}.pingr-title{font-size:2rem}[data-testid="stMetric"]{padding:11px 12px;min-height:88px}[data-testid="stMetricValue"]{font-size:1.4rem}}
@media(max-width:600px){.block-container{padding:.6rem .6rem 1.3rem}.pingr-title{font-size:1.75rem}[data-testid="stMetricLabel"]{font-size:.66rem}[data-testid="stMetricValue"]{font-size:1.18rem}}
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

st.sidebar.header("R2 connection")
today_label = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%d %b %Y")
st.sidebar.caption(f"Source: Cloudflare R2 · today only: {today_label} PKT")
if st.sidebar.button("Refresh archive now", use_container_width=True):
    st.cache_data.clear()
try:
    with st.spinner("Reading Pingr snapshots directly from Cloudflare R2…"):
        archive_files, archive_status = load_archive()
except Exception as exc:
    st.error(f"Could not read the Cloudflare R2 archive: {type(exc).__name__}: {exc}")
    st.info("Check that the deployed archive Worker exposes /dashboard/index and /dashboard/file.")
    st.stop()
uploads = [ArchiveUpload(name, content) for name, content in archive_files]
st.sidebar.metric("R2 objects loaded", f'{archive_status["loaded"]:,}')
st.sidebar.caption(f'Latest R2 object: {archive_status["updated"]}')
if archive_status["last_sync"]:
    st.sidebar.caption(f'Last GitHub mirror sync: {archive_status["last_sync"].get("completedAt", "status available")}')
if archive_status["errors"]:
    with st.sidebar.expander(f'{len(archive_status["errors"])} R2 object(s) could not be read'):
        st.write(archive_status["errors"])
else:
    st.sidebar.success("R2 archive read completed without file errors.")
st.sidebar.caption("Today’s R2 files only · automatic refresh every 2 hours · individual files cached by key, size and upload time.")

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

st.markdown('<div class="pingr-eyebrow">PINGR · LIVE INTELLIGENCE</div>', unsafe_allow_html=True)
st.markdown('<h1 class="pingr-title">PINGR <span>ANALYTICS</span></h1>', unsafe_allow_html=True)
st.markdown('<div class="pingr-subtitle">Decision-focused performance · Detector results · Coin intelligence · Latest archive activity</div><div class="pingr-rule"></div>', unsafe_allow_html=True)

# Keep the archive controls compact and out of the main analysis.
st.sidebar.caption("Bucket: pingr · prefix: pingr/logs/")
st.sidebar.caption("Manual refresh is available above.")


# High-level navigation: keep the primary intelligence visible without a long continuous scroll.
tab_overview, tab_scanner, tab_detectors, tab_coins, tab_quality, tab_logs = st.tabs([
    "Overview", "Scanner intelligence", "Detector performance", "Coin intelligence", "Signal quality", "Logs & diagnostics"
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
    left, right = st.columns(2)
    with left:
        st.subheader("Other event types in the logs")
        if not event_mix.empty:
            event_mix_df = event_mix.rename_axis("Event type").reset_index(name="Records")
            st.dataframe(event_mix_df, use_container_width=True, hide_index=True)
        else:
            st.info("No separate scanner/diagnostic event types were found in today's logs.")
    with right:
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
                     color="avg_return", color_continuous_scale=["#fb7185", "#263b58", "#20d6a0"],
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
