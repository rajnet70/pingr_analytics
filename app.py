import streamlit as st
import pandas as pd
import plotly.express as px
import json
import hashlib
import html
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
/* Prevent mobile viewport/page-level horizontal overflow. */
html,body{width:100%!important;max-width:100vw!important;overflow-x:hidden!important;box-sizing:border-box!important}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"],[data-testid="stMainBlockContainer"],.block-container{width:100%!important;max-width:100vw!important;min-width:0!important;overflow-x:hidden!important;box-sizing:border-box!important}
.winner-ledger,.winner-card,.winner-fields,.winner-field{width:100%;max-width:100%;min-width:0;box-sizing:border-box}
.winner-card{overflow-wrap:anywhere}
@media(max-width:767px){.block-container{padding-left:10px!important;padding-right:10px!important}.winner-fields{grid-template-columns:repeat(2,minmax(0,1fr))}.winner-card{margin-left:0!important;margin-right:0!important}}
:root{--bg:#030b16;--panel:#071a2b;--panel2:#0a2238;--line:rgba(22,177,238,.48);--cyan:#16c9f5;--blue:#168bd0;--ice:#91e8ff;--green:#39e75f;--red:#ff5b63;--muted:#9bb6cb;--text:#f2f8ff}
.stApp{background:radial-gradient(ellipse at 76% -8%,rgba(0,173,237,.20),transparent 36%),linear-gradient(145deg,#020813,#06182a 58%,#020b17);color:var(--text)}
.stApp:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.10;background:repeating-radial-gradient(circle at 0% 82%,transparent 0 26px,rgba(22,201,245,.55) 27px 28px,transparent 29px 43px);mask-image:linear-gradient(90deg,black,transparent 24%)}
.block-container{max-width:1800px;padding:1.25rem 1.5rem 2.5rem;position:relative}
[data-testid="stHeader"]{background:rgba(2,8,19,.82);backdrop-filter:blur(14px)}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#041322,#020b17)!important;border-right:1px solid rgba(22,177,238,.25)}
[data-testid="stSidebar"]>div{min-width:0}
[data-testid="stSidebarCollapseButton"],[data-testid="stSidebar"] button[kind="header"]{display:flex!important;visibility:visible!important;opacity:1!important;pointer-events:auto!important;z-index:1001!important}
@media(min-width:768px) and (max-width:1366px){[data-testid="stSidebar"]{width: min(260px, 28vw)!important}}
@media(max-width:767px){[data-testid="stSidebar"]{width:min(82vw, 320px)!important}}
[data-testid="stSidebar"]>div{padding-top:1rem}
[data-testid="stSidebar"] [data-testid="stRadio"] label{padding:11px 13px;border-radius:11px;color:#d9eaf7;font-weight:700;margin:3px 0}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover{background:rgba(0,177,238,.13)}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked){background:linear-gradient(100deg,#087fb8,#07528a);box-shadow:0 0 20px rgba(0,183,245,.27);color:white}
[data-testid="stSidebar"] [data-testid="stRadio"] input{accent-color:#16c9f5}
.sidebar-brand{display:flex;flex-direction:column;align-items:center;padding:8px 0 26px;border-bottom:1px solid rgba(22,177,238,.16);margin-bottom:20px}
.pingr-radar{width:62px;height:62px;border-radius:50%;background:repeating-radial-gradient(circle,transparent 0 3px,rgba(48,174,239,.72) 3.7px 4.5px,transparent 5px 8px);filter:drop-shadow(0 0 8px rgba(43,174,240,.25));position:relative}
.pingr-radar:after{content:"";position:absolute;width:8px;height:8px;border-radius:50%;background:#42b8f4;left:50%;top:50%;transform:translate(-50%,-50%);box-shadow:0 0 10px #42b8f4}
.pingr-wordmark{font-size:2.65rem;line-height:1.05;font-weight:400;letter-spacing:-.07em;color:#42b8f4;text-shadow:0 2px 0 #176b9e}
.sidebar-analytics{font-size:1.05rem;color:#dceefa;margin-top:6px}
.app-topline{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(22,177,238,.18);padding:4px 0 16px;margin-bottom:18px;color:#d8eaf8}
.app-topline>div:first-child{display:flex;flex-direction:column;gap:4px}
.top-eyebrow,.page-kicker{font-size:.66rem;letter-spacing:.19em;color:#54d7ff;font-weight:900}
.topline-right{display:flex;gap:18px;align-items:center;color:#9db9cf;font-size:.78rem}
.live-pill{border:1px solid rgba(57,231,95,.35);border-radius:999px;padding:7px 12px;color:#b9ffd0}
.live-pill i,.status-live{display:inline-block;width:8px;height:8px;background:#39e75f;border-radius:50%;margin-right:7px;box-shadow:0 0 10px #39e75f}
.page-heading{font-size:2rem;font-weight:900;letter-spacing:-.055em;color:#f4f9ff;margin-top:3px}
.page-subheading{color:#a9c4d9;font-size:.91rem;margin:0 0 17px}
.top-status{display:flex;align-items:center;gap:12px;color:#c4d8e9;font-size:.78rem;margin:5px 0 15px}
.top-status b{font-size:.65rem;letter-spacing:.1em;color:#9ebbd2}
.status-divider{height:30px;width:1px;background:rgba(22,177,238,.25);margin:0 5px}
.archive-meta{color:#8daac1}
.kpi-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:10px 0 18px}
.kpi-card{position:relative;display:grid;grid-template-columns:42px 1fr;grid-template-rows:auto auto;align-items:center;column-gap:8px;padding:13px 14px;border:1px solid rgba(22,177,238,.55);border-radius:16px;background:linear-gradient(145deg,rgba(8,34,56,.98),rgba(3,15,29,.98));box-shadow:0 0 16px rgba(0,177,238,.08),inset 0 1px rgba(255,255,255,.04);min-height:92px}
.kpi-icon{grid-row:1/3;font-size:1.8rem;color:#16c9f5;text-align:center}
.kpi-label{font-size:.78rem;color:#d6e7f4;font-weight:700}
.kpi-value{font-size:1.8rem;font-weight:900;color:#f7fbff;line-height:1.1}
.kpi-card.green .kpi-icon,.kpi-card.green .kpi-value{color:#39e75f}
.kpi-card.red .kpi-icon,.kpi-card.red .kpi-value{color:#ff5b63}
.panel-title{font-size:1.05rem;font-weight:900;color:#f1f8ff;padding:12px 14px 8px;border:1px solid rgba(22,177,238,.42);border-bottom:0;border-radius:15px 15px 0 0;background:linear-gradient(100deg,rgba(8,35,57,.98),rgba(4,18,32,.96))}
.panel-sub{font-size:.8rem;color:#8eb1c9;font-weight:500}
[data-testid="stPlotlyChart"],[data-testid="stDataFrame"]{border:1px solid rgba(22,177,238,.42);border-radius:0 0 15px 15px;overflow:hidden;background:rgba(5,21,37,.86);padding:4px}
[data-testid="stDataFrame"]{border-radius:12px}
[data-testid="stMetric"]{background:linear-gradient(145deg,rgba(8,34,56,.96),rgba(3,15,29,.98));border:1px solid rgba(22,177,238,.32);border-radius:14px;padding:13px 15px;min-height:86px}
[data-testid="stMetricLabel"]{color:#9ebbd2;font-size:.68rem;letter-spacing:.06em;text-transform:uppercase;font-weight:800}
[data-testid="stMetricValue"]{color:#f3f9ff;font-weight:900;font-size:1.55rem}
.mini-metric{display:flex;align-items:center;gap:8px;padding:10px 12px;border:1px solid rgba(22,177,238,.25);border-top:0;background:rgba(5,21,37,.84);font-size:.78rem}
.mini-metric:last-child{border-radius:0 0 12px 12px}
.mini-metric span{color:#c7ddec;flex:1}.mini-metric b{font-size:.78rem}.mini-metric i{color:#607b91;font-style:normal}
.positive{color:#39e75f}.negative{color:#ff5b63}
.insight-strip{display:flex;align-items:stretch;gap:0;border:1px solid rgba(22,177,238,.48);border-radius:15px;margin:18px 0;background:linear-gradient(100deg,rgba(7,29,49,.98),rgba(3,15,29,.98));overflow:hidden}
.insight-title{display:flex;align-items:center;padding:14px 18px;color:#55dfff;font-weight:900;letter-spacing:.08em;min-width:155px}
.insight-cell{display:flex;flex-direction:column;justify-content:center;padding:12px 18px;border-left:1px solid rgba(22,177,238,.28);flex:1;min-width:0}
.insight-cell small{font-size:.63rem;letter-spacing:.1em;color:#8daec5;font-weight:800}
.insight-cell b{font-size:1rem;color:#f2f8ff;margin:3px 0}
.insight-cell span{font-size:.76rem;color:#39e75f}
h1,h2,h3{letter-spacing:-.04em;color:var(--text)}
h2{font-size:1.2rem!important;margin:1rem 0 .7rem!important;font-weight:850!important}
h3{font-size:1rem!important;font-weight:800!important}
.stButton button,.stDownloadButton button{border-radius:10px;border:1px solid rgba(22,177,238,.52);min-height:40px;background:linear-gradient(110deg,#075d8e,#073a63);color:#f2f9ff;font-weight:800}
[data-testid="stExpander"]{border:1px solid rgba(22,177,238,.24);border-radius:12px;background:rgba(7,22,38,.84)}
[data-testid="stAlert"]{border-radius:12px}
hr{border-color:rgba(22,177,238,.16)!important}
@media(max-width:1100px){.kpi-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.insight-strip{flex-wrap:wrap}.insight-cell{min-width:30%}}
@media(max-width:750px){[data-testid="stSidebar"]{min-width:175px!important}.block-container{padding:.8rem .75rem 2rem}.kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.kpi-value{font-size:1.45rem}.page-heading{font-size:1.55rem}.topline-right{gap:7px;font-size:.66rem}.insight-title{min-width:100%;padding:10px 14px}.insight-cell{min-width:45%;padding:10px}.mini-metric{flex-wrap:wrap}}
/* Overview spacing and tablet-friendly table/chart hierarchy */
.top-status{margin:2px 0 13px}
.kpi-grid{grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin:10px 0 22px}
.kpi-card{min-height:88px;padding:12px 13px}
[data-testid="stDataFrame"]{width:100%;border-radius:0 0 14px 14px;margin-bottom:4px}
[data-testid="stDataFrame"] [data-testid="glideDataEditor"]{width:100%}
.mini-metric{min-height:48px;gap:7px;padding:11px 12px}
.mini-metric span{min-width:100px}
.panel-title{min-height:48px;display:flex;align-items:center;gap:8px}
@media(max-width:1050px){
 .kpi-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
 .mini-metric{flex-wrap:wrap}
 .mini-metric span{min-width:100%;flex-basis:100%}
}
@media(max-width:750px){
 .kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
 .block-container{padding:.75rem .7rem 2rem}
}

/* Responsive, vertically stacked winner ledger: never render a wide table on mobile. */
.winner-ledger{display:grid;grid-template-columns:minmax(0,1fr);gap:11px;margin:8px 0 4px}
.winner-card{min-width:0;border:1px solid rgba(22,177,238,.38);border-radius:13px;background:linear-gradient(145deg,rgba(8,30,49,.98),rgba(3,14,27,.98));padding:12px 13px;box-shadow:0 4px 16px rgba(0,0,0,.14)}
.winner-card-head{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:6px 12px;padding-bottom:9px;margin-bottom:9px;border-bottom:1px solid rgba(22,177,238,.22)}
.winner-card-title{font-size:.98rem;font-weight:900;color:#f3f9ff;overflow-wrap:anywhere}
.winner-card-pnl{font-size:1rem;font-weight:900;color:#39e75f;white-space:nowrap}
.winner-section-label{font-size:.62rem;letter-spacing:.12em;font-weight:900;color:#58d9ff;margin:9px 0 6px}
.winner-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}
.winner-field{min-width:0;border:1px solid rgba(22,177,238,.14);border-radius:8px;background:rgba(2,12,23,.55);padding:7px 8px}
.winner-field-label{display:block;color:#91abc0;font-size:.62rem;font-weight:800;letter-spacing:.04em;margin-bottom:3px}
.winner-field-value{display:block;color:#f0f6fc;font-size:.79rem;font-weight:700;overflow-wrap:anywhere;word-break:break-word}
.winner-field-value.missing{color:#9bb0c1;font-weight:500}
.winner-card-meta{color:#829db2;font-size:.66rem;margin-top:9px;overflow-wrap:anywhere}
@media(max-width:560px){.winner-card{padding:10px}.winner-fields{grid-template-columns:repeat(2,minmax(0,1fr))}.winner-card-title{font-size:.9rem}.winner-field-value{font-size:.75rem}}

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
    # R2 stores archives in date-based folders. The dashboard analysis window
    # starts on 27 November 2026 and includes every later dated folder.
    archive_start_date = datetime(2026, 11, 27).date()
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

    # Include compressed JSONL archives from 27 Nov 2026 onwards.
    # Expected R2 key layout: pingr/logs/YYYY/MM/DD/<archive>.gz
    archives = []
    for item in objects:
        key = item.get("key", "").lstrip("/")
        if not key.lower().endswith(".gz") or not key.startswith("pingr/logs/"):
            continue
        parts = key.split("/")
        if len(parts) < 5:
            continue
        try:
            folder_date = datetime.strptime("/".join(parts[2:5]), "%Y/%m/%d").date()
        except ValueError:
            continue
        if folder_date < archive_start_date:
            continue
        archives.append({
            "key": item["key"],
            "name": key.rsplit("/", 1)[-1],
            "size": item.get("size", 0),
            "uploaded": item.get("uploaded")
        })
    archives.sort(key=lambda item: (item.get("uploaded") or "", item["key"]))
    return archives, last_run

def load_archive():
    # Return only the paginated object index. File contents are fetched and parsed
    # sequentially below so multiple large decompressed archives are never resident
    # in Streamlit memory at the same time.
    objects, last_run = r2_archive_index()
    latest = max((item.get("uploaded") or item["name"] for item in objects), default="Not available")
    return objects, {
        "files": len(objects),
        "loaded": 0,
        "errors": [],
        "updated": latest,
        "last_sync": last_run,
        "objects": objects
    }

def parse_r2_archives(objects):
    per_file = {}
    all_records = []
    errors = []
    seen_global = set()
    duplicate_count = 0
    loaded_count = 0
    latest_name = None
    latest_rows = []

    for item in objects:
        rows = []
        try:
            response = requests.get(
                R2_FILE_URL,
                params={"key": item["key"]},
                timeout=(15, 180),
                stream=True
            )
            response.raise_for_status()
            # Worker response is JSONL. Iterate lines from the response body,
            # parse each record, then release the response before next object.
            for line_no, raw_line in enumerate(response.iter_lines(), 1):
                if not raw_line:
                    continue
                try:
                    obj = json.loads(raw_line.decode("utf-8-sig", errors="replace"))
                    if not isinstance(obj, dict):
                        raise ValueError("JSON line is not an object")
                    fingerprint = hashlib.sha256(
                        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()
                    ).hexdigest()
                    if fingerprint in seen_global:
                        duplicate_count += 1
                        continue
                    seen_global.add(fingerprint)
                    record = dict(obj)
                    record["_source_file"] = item["name"]
                    record["_line"] = line_no
                    all_records.append(record)
                    rows.append(record)
                except Exception as exc:
                    errors.append({"file": item["name"], "line": line_no, "error": str(exc)})
            response.close()
            loaded_count += 1
            latest_name = item["name"]
            latest_rows = rows
        except Exception as exc:
            errors.append({"file": item["name"], "line": 0, "error": f"{type(exc).__name__}: {exc}"})
            try:
                response.close()
            except Exception:
                pass

    if latest_name is not None:
        per_file[latest_name] = latest_rows
    return per_file, all_records, errors, duplicate_count, loaded_count

today_label = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%d %b %Y")
control_left, control_right = st.columns([1, 5])
with control_left:
    if st.button("↻  Refresh archive", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with control_right:
    st.markdown(
        f'<div style="padding:10px 14px;border:1px solid rgba(66,184,244,.18);border-radius:11px;background:rgba(8,24,40,.72);color:#a9c5da;font-size:.82rem">'
        f'<strong style="color:#72cefa">CLOUDFLARE R2</strong> &nbsp;·&nbsp; Archive folders from 27 Nov 2026'
        f' &nbsp;·&nbsp; Auto-refresh every 2 hours &nbsp;·&nbsp; Source: pingr/logs/ · Start: 27 Nov 2026</div>',
        unsafe_allow_html=True
    )
try:
    with st.spinner("Reading the R2 archive index…"):
        archive_objects, archive_status = load_archive()
except Exception as exc:
    st.error(f"Could not read the Cloudflare R2 archive index: {type(exc).__name__}: {exc}")
    st.info("Check that the archive Worker exposes /dashboard/index.")
    st.stop()


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



def enrich_alert_records_with_outcomes(alert_records, outcomes, tolerance_seconds=180):
    """
    Attach outcome data only when an alert_record can be uniquely linked.
    Build 4.4.1 creates alert_id as SYMBOL_<unix-seconds> immediately before
    Discord dispatch; build_alert_record captures alert_time after dispatch and
    additional market-data lookups. A 15-second tolerance can therefore miss
    the correct outcome. Allow up to 180 seconds, but still require exact symbol,
    one unique candidate ID, and one-to-one ID usage. Symbol-only joins are forbidden.
    """
    base = alert_records.copy().reset_index(drop=True)
    latest = latest_outcomes(outcomes)
    base["matched_alert_id"] = pd.NA
    base["outcome_match_status"] = "No unique alert_id/time match"
    if base.empty or latest.empty or not {"alert_id", "symbol"}.issubset(latest.columns):
        return base

    outcome_by_id = {}
    parsed_outcomes = latest.copy()
    parsed_outcomes["_id_symbol"] = parsed_outcomes["alert_id"].astype(str).str.rsplit("_", n=1).str[0]
    parsed_outcomes["_id_epoch"] = pd.to_numeric(
        parsed_outcomes["alert_id"].astype(str).str.extract(r"_(\d{10})$")[0],
        errors="coerce"
    )
    for _, outcome in parsed_outcomes.dropna(subset=["_id_epoch"]).iterrows():
        outcome_by_id[str(outcome["alert_id"])] = outcome

    candidates_by_row = {}
    for idx, alert in base.iterrows():
        direct_id = alert.get("alert_id")
        if pd.notna(direct_id) and str(direct_id) in outcome_by_id:
            candidates_by_row[idx] = [str(direct_id)]
            continue

        alert_symbol = str(alert.get("symbol", "")).strip()
        alert_time_value = alert.get("alert_time", alert.get("timestamp"))
        alert_time = pd.to_datetime(alert_time_value, errors="coerce", utc=True)
        if not alert_symbol or pd.isna(alert_time):
            candidates_by_row[idx] = []
            continue
        alert_epoch = alert_time.timestamp()
        matches = parsed_outcomes[
            parsed_outcomes["_id_symbol"].eq(alert_symbol)
            & parsed_outcomes["_id_epoch"].notna()
            & ((parsed_outcomes["_id_epoch"] - alert_epoch).abs() <= tolerance_seconds)
        ]["alert_id"].astype(str).drop_duplicates().tolist()
        candidates_by_row[idx] = matches

    id_usage = {}
    for ids in candidates_by_row.values():
        # Count every possible claim, including candidates from ambiguous rows.
        # This prevents another row from consuming an ID that is also ambiguous.
        for alert_id in set(ids):
            id_usage[alert_id] = id_usage.get(alert_id, 0) + 1

    outcome_fields = [
        col for col in latest.columns
        if col.startswith("original_") or col in {
            "pnl_percent", "mfe_percent", "mae_percent", "result", "timestamp",
            "entry_price", "exit_price", "timeframe"
        }
    ]
    for field in outcome_fields:
        if field not in base.columns:
            base[field] = pd.NA

    for idx, ids in candidates_by_row.items():
        if len(ids) != 1:
            base.at[idx, "outcome_match_status"] = (
                "Ambiguous: multiple candidate IDs" if len(ids) > 1 else "Unmatched: no verified ID"
            )
            continue
        alert_id = ids[0]
        if id_usage.get(alert_id, 0) != 1:
            base.at[idx, "outcome_match_status"] = "Ambiguous: ID maps to multiple alert records"
            continue
        outcome = outcome_by_id.get(alert_id)
        if outcome is None:
            continue
        base.at[idx, "matched_alert_id"] = alert_id
        base.at[idx, "outcome_match_status"] = "Matched by alert_id"
        for field in outcome_fields:
            base.at[idx, field] = outcome.get(field, pd.NA)

    return base


def compact_volume(value):
    if pd.isna(value):
        return "—"
    value = float(value)
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:.0f}"


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



if not archive_objects:
    st.warning("No compressed JSONL log files were found in the R2 archive.")
    st.stop()

with st.spinner(f"Processing {len(archive_objects):,} R2 archive files sequentially…"):
    per_file, combined_rows, errors, duplicate_count, loaded_count = parse_r2_archives(archive_objects)
archive_status["loaded"] = loaded_count
archive_status["errors"] = errors
if errors:
    with st.expander(f'{len(errors)} R2 file/line issue(s) encountered'):
        st.write(errors[:200])
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
st.sidebar.markdown(
    '<div class="sidebar-brand"><div class="pingr-radar"></div><div class="pingr-wordmark">pingr</div><div class="sidebar-analytics">Analytics</div></div>',
    unsafe_allow_html=True
)
page_options = ["Overview","Signals","Performance","Patterns","Symbols","Logs & Archives","Settings"]
active_page = st.sidebar.radio("NAVIGATION",page_options,label_visibility="collapsed",key="pingr_primary_navigation")
page_map = {
    "Overview":"Overview", "Signals":"Scanner intelligence",
    "Performance":"Detector performance", "Patterns":"Patterns",
    "Symbols":"Coin intelligence", "Logs & Archives":"Logs & diagnostics",
    "Settings":"Signal quality"
}
active_page = page_map[active_page]
st.markdown(
    f'<div class="app-topline"><div><span class="top-eyebrow">PINGR / ANALYTICS</span><b>{today_hero_label}</b></div>'
    f'<div class="topline-right"><span class="live-pill"><i></i> R2 CONNECTED</span><span class="top-cycle">2-HOUR ARCHIVE CYCLE</span></div></div>',
    unsafe_allow_html=True
)
# The tracker ledger is the source of truth for the 13 closed winners.
# alert_outcome contains separate 5m/15m/30m evaluations and must not replace
# the final closed alert_record classification used by the dashboard KPIs.
overview_outcomes = latest_outcomes(outcomes)
outcome_results = overview_outcomes.get("result", pd.Series(dtype="object")).astype(str).str.lower()
classified_outcomes = overview_outcomes[outcome_results.isin(["win", "loss", "neutral"])].copy()
closed_count = len(valid)
tracker_returns = pd.to_numeric(valid.get("final_percent", pd.Series(dtype="float64")), errors="coerce")
wins = int((tracker_returns >= 1.0).sum())
losses = int((tracker_returns <= -0.5).sum())
neutral = max(0, closed_count - wins - losses)
decisive = wins + losses
win_rate = wins / closed_count * 100 if closed_count else float("nan")
decisive_rate = wins / decisive * 100 if decisive else float("nan")
avg_return = tracker_returns.mean() if closed_count else float("nan")
latest_alert_time = alerts["_ts"].max() if not alerts.empty and "_ts" in alerts else pd.NaT
if pd.isna(latest_alert_time):
    latest_alert_time = latest_time
latest_alert_label = (latest_alert_time.tz_convert("Asia/Karachi").strftime("%d %b %Y, %H:%M PKT")
                      if pd.notna(latest_alert_time) else "Timestamp unavailable")
classified = pd.DataFrame()
pattern_rows = []
winner_n = loser_n = 0
summary_df = pd.DataFrame()
liquidity_field = None
macd_fields = []
if not overview_outcomes.empty and {"symbol", "result"}.issubset(overview_outcomes.columns):
    overview_outcomes = overview_outcomes.copy()
    overview_outcomes["result"] = overview_outcomes["result"].astype(str).str.lower()
    numeric_fields = [
        "pnl_percent", "original_volume_5m", "original_price_change_5m",
        "original_rsi_15m", "original_score", "original_liquidity",
        "original_liquidity_usd", "original_quote_volume_24h",
        "original_volume_24h", "original_turnover_24h"
    ]
    for field in numeric_fields:
        if field in overview_outcomes:
            overview_outcomes[field] = pd.to_numeric(overview_outcomes[field], errors="coerce")
    liquidity_fields = [
        col for col in overview_outcomes.columns
        if any(token in col.lower() for token in ("liquidity", "quote_volume", "turnover_24h", "volume_24h"))
        and pd.api.types.is_numeric_dtype(overview_outcomes[col])
    ]
    liquidity_field = next((col for col in liquidity_fields if "original" in col.lower()),
                           liquidity_fields[0] if liquidity_fields else None)
    indicator_fields = [
        ("original_score", "Signal score"),
        ("original_volume_5m", "5m volume ratio"),
        ("original_price_change_5m", "5m price change %"),
        ("original_rsi_15m", "15m RSI"),
    ]
    if liquidity_field:
        indicator_fields.append((liquidity_field, "24h Quote Vol"))
    macd_fields = [
        (field, label) for field, label in [
            ("original_macd_5m", "MACD 5m"),
            ("original_macd_15m", "MACD 15m"),
            ("original_macd_1h", "MACD 1h")
        ] if field in overview_outcomes.columns
    ]
    classified = overview_outcomes[overview_outcomes["result"].isin(["win", "loss", "neutral"])].copy()
    if not classified.empty:
        classified["symbol"] = classified["symbol"].fillna("Unknown").astype(str)
        summary_rows = []
        for result_name, display_name in [("win", "Winners"), ("loss", "Losers"), ("neutral", "Neutral")]:
            group = classified[classified["result"].eq(result_name)]
            row = {"Group": display_name, "Alerts": len(group)}
            if "pnl_percent" in group:
                row["Median P&L %"] = group["pnl_percent"].median()
            for field, label in indicator_fields:
                if field in group:
                    field_values = pd.to_numeric(group[field], errors="coerce").dropna()
                    if label == "24h Quote Vol":
                        row["24h Quote Vol Min"] = field_values.min() if not field_values.empty else float("nan")
                        row["24h Quote Vol Max"] = field_values.max() if not field_values.empty else float("nan")
                    else:
                        row[label] = field_values.median() if not field_values.empty else float("nan")
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
            if abs(value) >= 1_000_000_000:
                return f"{value / 1_000_000_000:.2f}B"
            if abs(value) >= 1_000_000:
                return f"{value / 1_000_000:.1f}M"
            if abs(value) >= 1_000:
                return f"{value / 1_000:.1f}K"
            return f"{value:.0f}"

        pattern_specs = [
            ("original_rsi_15m", "15m RSI", "number"),
            ("original_volume_5m", "5m volume ratio", "multiple"),
            ("original_score", "Signal score", "number"),
            ("original_price_change_5m", "5m price change", "percent"),
        ]
        if liquidity_field:
            pattern_specs.insert(1, (liquidity_field, "24h quote volume", "volume"))
        winner_n = int(classified["result"].eq("win").sum())
        loser_n = int(classified["result"].eq("loss").sum())
        for field, label, kind in pattern_specs:
            if field not in classified.columns:
                continue
            row = {"Pattern": label}
            for result_name, prefix in [("win", "Winners"), ("loss", "Losers")]:
                values = pd.to_numeric(classified.loc[classified["result"].eq(result_name), field], errors="coerce").dropna()
                if values.empty:
                    row[prefix] = "No data"
                    row[prefix + " n"] = 0
                    continue
                if kind == "volume":
                    row[prefix] = f"Min {compact_volume(values.min())} · Max {compact_volume(values.max())}"
                else:
                    low, median, high = values.quantile([.25, .50, .75]).tolist()
                if kind == "percent":
                    row[prefix] = f"{low:+.2f}%–{high:+.2f}% (med {median:+.2f}%)"
                elif kind == "multiple":
                    row[prefix] = f"{low:.2f}×–{high:.2f}× (med {median:.2f}×)"
                else:
                    row[prefix] = f"{low:.1f}–{high:.1f} (med {median:.1f})"
                row[prefix + " n"] = len(values)
            pattern_rows.append(row)

# Rank symbols from closed tracked-alert records; do not invent symbol-level results.
if closed_count and "symbol" in valid.columns:
    symbol_data = valid.copy()
    symbol_data["final_percent"] = pd.to_numeric(symbol_data["final_percent"], errors="coerce")
    symbol_data = symbol_data.dropna(subset=["symbol", "final_percent"])
    symbol_rank = symbol_data.groupby("symbol").agg(
        signals=("final_percent", "size"),
        wins=("final_percent", lambda x: int((x >= 1.0).sum())),
        losses=("final_percent", lambda x: int((x <= -.5).sum())),
        median_pnl=("final_percent", "median"),
    ).reset_index()
    symbol_rank["avg_score"] = (
        symbol_data.groupby("symbol")["signal_score"].mean().reindex(symbol_rank["symbol"]).to_numpy()
        if "signal_score" in symbol_data else float("nan")
    )
    symbol_rank["decisive"] = symbol_rank["wins"] + symbol_rank["losses"]
    symbol_rank["win_rate"] = (symbol_rank["wins"] / symbol_rank["decisive"].replace(0, pd.NA) * 100)
    symbol_rank = symbol_rank.sort_values(["win_rate", "signals"], ascending=[False, False], na_position="last")
    symbol_rank["Signal"] = "MIXED"
    if "detector" in symbol_data:
        direction = symbol_data.groupby("symbol")["detector"].agg(lambda x: str(x.mode().iloc[0]) if not x.mode().empty else "MIXED")
        symbol_rank["Signal"] = symbol_rank["symbol"].map(direction).fillna("MIXED")
    symbol_rank_view = symbol_rank.rename(columns={
        "symbol":"Symbol", "signals":"Signals", "wins":"Wins", "losses":"Losses",
        "win_rate":"Win Rate", "median_pnl":"Median P&L", "avg_score":"Score (Avg)"
    })
    symbol_rank_view = symbol_rank_view[["Symbol","Signal","Signals","Wins","Losses","Win Rate","Median P&L","Score (Avg)"]]
    symbol_rank_view["Win Rate"] = symbol_rank_view["Win Rate"].map(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
    symbol_rank_view["Median P&L"] = symbol_rank_view["Median P&L"].map(lambda x: f"{x:+.2f}%")
    symbol_rank_view["Score (Avg)"] = symbol_rank_view["Score (Avg)"].map(lambda x: f"{x:.1f}" if pd.notna(x) else "—")
else:
    symbol_rank_view = pd.DataFrame()


if active_page == "Overview":
    st.markdown('<div class="page-kicker">01 / COMMAND CENTRE</div><div class="page-heading">Signal Intelligence</div><div class="page-subheading">Performance, patterns and insights from Pingr signal archives.</div>', unsafe_allow_html=True)

    # Keep winner/loser counts, symbol performance, comparison metrics and individual
    # winning-alert liquidity in one visually grouped area to prevent split interpretations.
    with st.container(border=True):
        st.markdown("### Signal & Winner Intelligence")
        st.caption("One consolidated view: overall results, symbol performance, winner-versus-loser indicators and every winning alert.")
        # Header status and compact KPI row.
        st.markdown(
            f'<div class="top-status"><span class="status-live"></span><span><b>LAST ARCHIVE UPDATE</b><br>{latest_alert_label}</span>'
            f'<span class="status-divider"></span><span class="archive-meta">{len(combined):,} events · {archive_status["loaded"]:,} R2 files</span></div>',
            unsafe_allow_html=True
        )
        kpis = [
            ("◉", "Total Signals", f"{len(alerts):,}", "cyan"),
            ("🏆", "Win Rate", f"{win_rate:.1f}%" if pd.notna(win_rate) else "—", "green"),
            ("◎", "Decisive Win Rate", f"{decisive_rate:.1f}%" if pd.notna(decisive_rate) else "—", "green"),
            ("↗", "Winners", f"{wins:,}", "green"),
            ("↘", "Losers", f"{losses:,}", "red"),
        ]
        kpi_html = "".join(
            f'<div class="kpi-card {tone}"><div class="kpi-icon">{icon}</div><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div></div>'
            for icon,label,value,tone in kpis
        )
        st.markdown(f'<div class="kpi-grid">{kpi_html}</div>', unsafe_allow_html=True)

        # One row per closed tracker winner. Use alert_record for final P&L and
        # its original indicators; enrich from alert_outcome and nearby R2 quality
        # snapshots only when symbol AND event time establish a safe match.
        st.markdown('<div class="panel-title">Winners · complete R2 signal and liquidity ledger</div>', unsafe_allow_html=True)
        winner_returns = pd.to_numeric(valid.get("final_percent", pd.Series(dtype="float64")), errors="coerce")
        winning_alerts = valid[winner_returns >= 1.0].copy() if not valid.empty else pd.DataFrame()

        if not winning_alerts.empty:
            enriched = enrich_alert_records_with_outcomes(winning_alerts, outcomes)

            # R2 writes two different quality snapshots for the same symbol:
            # post_market_data_pre_gates contains liquidity/volume/price, while
            # post_indicator_pre_rsi_gate contains RSI and MACD. Do not let the
            # nearest pre-indicator snapshot mask fields from the indicator snapshot.
            # Each match still requires same symbol + nearest timestamp <=180s;
            # equidistant ties are rejected and no symbol-only join is allowed.
            quality = combined[combined.get("event_type", pd.Series(index=combined.index, dtype="object")).eq("signal_quality_snapshot")].copy()
            quality["_quality_ts"] = pd.to_datetime(quality.get("timestamp", pd.Series(index=quality.index)), errors="coerce", utc=True)
            quality["_quality_stage"] = quality.get("diagnostic.stage", pd.Series("", index=quality.index)).fillna("").astype(str)
            quality["_quality_symbol"] = quality.get("symbol", pd.Series("", index=quality.index)).fillna("").astype(str)
            quality_fields = [
                "quality_volume_24h", "quality_volume_5m", "quality_volume_15m",
                "quality_price_5m", "quality_price_15m", "quality_rsi_15m"
            ]
            for field in quality_fields:
                enriched[field] = pd.NA
            enriched["quality_market_match_status"] = "No unique market snapshot within 180s"
            enriched["quality_indicator_match_status"] = "No unique indicator snapshot within 180s"

            def nearest_quality_snapshot(alert, stage):
                alert_time = pd.to_datetime(alert.get("alert_time"), errors="coerce", utc=True)
                if pd.isna(alert_time) or quality.empty:
                    return None
                candidates = quality[
                    quality["_quality_symbol"].eq(str(alert.get("symbol", "")))
                    & quality["_quality_stage"].eq(stage)
                ].copy()
                if candidates.empty:
                    return None
                candidates["_gap_seconds"] = (candidates["_quality_ts"] - alert_time).abs().dt.total_seconds()
                candidates = candidates[
                    candidates["_gap_seconds"].notna() & (candidates["_gap_seconds"] <= 180)
                ].sort_values("_gap_seconds")
                if candidates.empty:
                    return None
                if len(candidates) > 1 and abs(
                    float(candidates.iloc[1]["_gap_seconds"]) - float(candidates.iloc[0]["_gap_seconds"])
                ) < 0.001:
                    return None
                return candidates.iloc[0]

            for idx, alert in enriched.iterrows():
                market = nearest_quality_snapshot(alert, "post_market_data_pre_gates")
                if market is not None:
                    enriched.at[idx, "quality_volume_24h"] = market.get("diagnostic.volume_24h_quote_usdt", pd.NA)
                    enriched.at[idx, "quality_volume_5m"] = market.get("diagnostic.volume_spike_5m", pd.NA)
                    enriched.at[idx, "quality_volume_15m"] = market.get("diagnostic.volume_spike_15m", pd.NA)
                    enriched.at[idx, "quality_price_5m"] = market.get("diagnostic.price_change_5m_pct", pd.NA)
                    enriched.at[idx, "quality_price_15m"] = market.get("diagnostic.price_change_15m_pct", pd.NA)
                    enriched.at[idx, "quality_market_match_status"] = "Matched market snapshot"

                indicators = nearest_quality_snapshot(alert, "post_indicator_pre_rsi_gate")
                if indicators is not None:
                    enriched.at[idx, "quality_rsi_15m"] = indicators.get("diagnostic.rsi_15m", pd.NA)
                    enriched.at[idx, "quality_indicator_match_status"] = "Matched indicator snapshot"

            # Winner-only aggregate pattern analysis, grouped by the recorded alert detector/type.
            # Uses the already verified winner set and the stage-specific R2 quality matches above.
            st.markdown("#### Winner patterns by alert type")
            st.caption("Closed winners only (final P&L ≥ +1%). Alert type is the recorded detector. Each metric has its own captured sample count; unmatched or missing values are excluded, never inferred.")

            winner_pattern_frame = enriched.copy()
            winner_pattern_frame["_alert_type"] = winner_pattern_frame.get(
                "detector", pd.Series("Unknown", index=winner_pattern_frame.index)
            ).fillna("Unknown").astype(str).replace("", "Unknown")

            winner_pattern_metrics = [
                ("24h quote liquidity (USDT)", ["quality_volume_24h"], "volume"),
                ("5m volume ratio", ["quality_volume_5m"], "multiple"),
                ("15m volume ratio", ["quality_volume_15m"], "multiple"),
                ("5m price change", ["quality_price_5m"], "percent"),
                ("15m price change", ["quality_price_15m"], "percent"),
                ("15m RSI", ["quality_rsi_15m"], "number"),
                ("Signal score", ["signal_score", "score"], "number"),
            ]

            def winner_pattern_values(frame, fields):
                values = pd.Series(index=frame.index, dtype="float64")
                for field in fields:
                    if field in frame.columns:
                        values = values.combine_first(pd.to_numeric(frame[field], errors="coerce"))
                return values

            pattern_table_rows = []
            for alert_type, type_frame in winner_pattern_frame.groupby("_alert_type", dropna=False):
                for metric_label, candidates, kind in winner_pattern_metrics:
                    vals = winner_pattern_values(type_frame, candidates).dropna()
                    if vals.empty:
                        minimum = average = maximum = "Not captured"
                    else:
                        lo, avg, hi = vals.min(), vals.mean(), vals.max()
                        if kind == "volume":
                            fmt = lambda x: compact_volume(x) + " USDT"
                        elif kind == "multiple":
                            fmt = lambda x: f"{x:.2f}×"
                        elif kind == "percent":
                            fmt = lambda x: f"{x:+.2f}%"
                        else:
                            fmt = lambda x: f"{x:.2f}"
                        minimum, average, maximum = fmt(lo), fmt(avg), fmt(hi)
                    pattern_table_rows.append({
                        "Alert type": str(alert_type),
                        "Winner count": int(len(type_frame)),
                        "Metric": metric_label,
                        "Minimum": minimum,
                        "Average": average,
                        "Maximum": maximum,
                        "Captured n": int(vals.size),
                    })

            if pattern_table_rows:
                st.dataframe(
                    pd.DataFrame(pattern_table_rows),
                    use_container_width=True,
                    hide_index=True,
                    height=min(42 * (len(pattern_table_rows) + 1) + 8, 720),
                )
                st.caption("Market measurements come only from the unique, timestamp-matched R2 quality snapshots for each winner. Score and alert type come from the alert record. Absolute traded volume is not inferred from volume ratios.")
            else:
                st.info("No winner records are available for alert-type pattern analysis.")

            def first_numeric(frame, fields):
                values = pd.Series(index=frame.index, dtype="float64")
                for field in fields:
                    if field in frame.columns:
                        values = values.combine_first(pd.to_numeric(frame[field], errors="coerce"))
                return values

            winner_view = pd.DataFrame(index=enriched.index)
            parsed_time = pd.to_datetime(enriched.get("alert_time", pd.Series(index=enriched.index)), errors="coerce", utc=True)
            winner_view["Alert time (PKT)"] = parsed_time.dt.tz_convert("Asia/Karachi").dt.strftime("%d %b · %H:%M:%S").fillna("—")
            winner_view["Symbol"] = enriched.get("symbol", pd.Series("Unknown", index=enriched.index)).fillna("Unknown")
            winner_view["Signal"] = enriched.get("detector", pd.Series("Unknown", index=enriched.index)).fillna("Unknown")

            # Prefer exact fields from the R2 alert/outcome records, then fill gaps
            # from the timestamp- and stage-matched R2 quality snapshots.
            score = first_numeric(enriched, ["signal_score", "score", "original_score"])
            volume5 = first_numeric(enriched, ["original_volume_5m", "volume_spike_5m", "quality_volume_5m"])
            volume15 = first_numeric(enriched, ["original_volume_15m", "volume_spike_15m", "vol_ratio", "quality_volume_15m"])
            price5 = first_numeric(enriched, ["original_price_change_5m", "price_change_5m", "quality_price_5m"])
            price15 = first_numeric(enriched, ["original_price_change_15m", "price_change_15m", "quality_price_15m"])
            rsi15 = first_numeric(enriched, ["rsi_15m", "rsi_14", "rsi", "original_rsi_15m", "quality_rsi_15m"])
            liquidity = first_numeric(enriched, ["original_volume_24h", "original_quote_volume_24h", "original_turnover_24h", "volume_24h_quote_usdt", "quality_volume_24h"]).replace(0, float("nan"))
            pnl = first_numeric(enriched, ["final_percent"])
            peak = first_numeric(enriched, ["peak_percent"])
            worst = first_numeric(enriched, ["worst_percent"])
            held = first_numeric(enriched, ["minutes_held"])

            winner_view["Score"] = score.map(lambda x: f"{x:.1f}" if pd.notna(x) else "—")
            winner_view["5m volume ratio"] = volume5.map(lambda x: f"{x:.2f}×" if pd.notna(x) else "—")
            winner_view["15m volume ratio"] = volume15.map(lambda x: f"{x:.2f}×" if pd.notna(x) else "—")
            winner_view["5m price change"] = price5.map(lambda x: f"{x:+.2f}%" if pd.notna(x) else "—")
            winner_view["15m price change"] = price15.map(lambda x: f"{x:+.2f}%" if pd.notna(x) else "—")
            winner_view["15m RSI"] = rsi15.map(lambda x: f"{x:.1f}" if pd.notna(x) else "—")
            winner_view["24h quote liquidity (USDT)"] = liquidity.map(
                lambda x: compact_volume(x) if pd.notna(x) else "Not captured"
            )
            winner_view["Peak move"] = peak.map(lambda x: f"{x:+.2f}%" if pd.notna(x) else "—")
            winner_view["Worst move"] = worst.map(lambda x: f"{x:+.2f}%" if pd.notna(x) else "—")
            winner_view["Final P&L"] = pnl.map(lambda x: f"{x:+.2f}%" if pd.notna(x) else "—")
            winner_view["Minutes held"] = held.map(lambda x: f"{x:.1f}" if pd.notna(x) else "—")
            winner_view["Exit reason"] = enriched.get("exit_reason", pd.Series("—", index=enriched.index)).fillna("—")

            winner_view["_sort_pnl"] = pnl
            winner_view = winner_view.sort_values("_sort_pnl", ascending=False, na_position="last").drop(columns=["_sort_pnl"])
            winner_columns = [
                "Alert time (PKT)", "Symbol", "Signal", "Score",
                "5m volume ratio", "15m volume ratio", "5m price change", "15m price change", "15m RSI",
                "24h quote liquidity (USDT)",
                "Peak move", "Worst move", "Final P&L", "Minutes held", "Exit reason"
            ]
            winner_view = winner_view[winner_columns]

            # Stage 1: compact native Streamlit leaderboard. Keep the existing
            # R2 parsing, matching, winner calculations and detail fields untouched.
            leaderboard = winner_view[
                ["Symbol", "Final P&L", "Peak move", "24h quote liquidity (USDT)"]
            ].copy()
            leaderboard.insert(0, "Rank", range(1, len(leaderboard) + 1))
            st.dataframe(
                leaderboard,
                use_container_width=True,
                hide_index=True,
                height=min(42 * (len(leaderboard) + 1) + 8, 720),
                column_config={
                    "Rank": st.column_config.NumberColumn("Rank", format="%d", width="small"),
                    "Symbol": st.column_config.TextColumn("Symbol", width="medium"),
                    "Final P&L": st.column_config.TextColumn("Final P&L", width="small"),
                    "Peak move": st.column_config.TextColumn("Peak move", width="small"),
                    "24h quote liquidity (USDT)": st.column_config.TextColumn(
                        "24h liquidity (USDT)", width="medium"
                    ),
                },
            )

                        # Details are embedded in each native expander. This avoids a
            # separate selection widget and keeps all winner records independently accessible.
            detail_fields = [
                ("Alert time (PKT)", "Alert time (PKT)"),
                ("Symbol", "Symbol"),
                ("Signal / detector", "Signal"),
                ("Signal score", "Score"),
                ("5m volume ratio", "5m volume ratio"),
                ("15m volume ratio", "15m volume ratio"),
                ("5m price change", "5m price change"),
                ("15m price change", "15m price change"),
                ("15m RSI", "15m RSI"),
                ("24h quote liquidity (USDT)", "24h quote liquidity (USDT)"),
                ("Peak move", "Peak move"),
                ("Worst move", "Worst move"),
                ("Final P&L", "Final P&L"),
                ("Minutes held", "Minutes held"),
                ("Exit reason", "Exit reason"),
            ]

            for rank, (_, winner) in enumerate(winner_view.iterrows(), 1):
                label = (
                    f"#{rank} · {winner['Symbol']} · {winner['Final P&L']} "
                    f"· Peak {winner['Peak move']}"
                )
                with st.expander(label, expanded=False):
                    detail_rows = []
                    for field_label, column in detail_fields:
                        value = winner.get(column, "Not captured")
                        if value is None or (isinstance(value, float) and pd.isna(value)):
                            value = "Not captured"
                        value = str(value).strip()
                        if value in ("", "—", "nan", "None"):
                            value = "Not captured"
                        detail_rows.append({"Field": field_label, "Value": value})

                    st.dataframe(
                        pd.DataFrame(detail_rows),
                        use_container_width=True,
                        hide_index=True,
                        height= min(38 * (len(detail_rows) + 1) + 8, 620),
                        column_config={
                            "Field": st.column_config.TextColumn("Field", width="medium"),
                            "Value": st.column_config.TextColumn("Value", width="large"),
                        },
                    )

            liquidity_count = int((winner_view["24h quote liquidity (USDT)"] != "Not captured").sum())
            st.caption(
                f"{len(winner_view)} closed winning alert records · {liquidity_count}/{len(winner_view)} with 24h quote liquidity "
                "from a linked outcome or stage-specific same-symbol R2 quality snapshot within 3 minutes. "
                "No symbol-only joins; unavailable source values remain explicitly marked."
            )
        else:
            st.info("No closed winning alert records (final P&L ≥ +1%) were found in the current R2 archive.")

    # Compact insight strip from actual sample observations.
    insight_items=[]
    if closed_count and "symbol" in valid.columns and not symbol_rank.empty:
        best=symbol_rank.iloc[0]
        if pd.notna(best["win_rate"]):
            insight_items.append(("TOP PERFORMER",str(best["symbol"]),f'{best["win_rate"]:.1f}% win rate',"green"))
        most=symbol_rank.sort_values("signals",ascending=False).iloc[0]
        insight_items.append(("MOST ACTIVE",str(most["symbol"]),f'{int(most["signals"])} signals',"cyan"))
    if pd.notna(decisive_rate):
        insight_items.append(("DECISIVE WIN RATE",f"{decisive_rate:.1f}%","Wins / (wins + losses)","green"))
    if insight_items:
        cells="".join(f'<div class="insight-cell"><small>{a}</small><b>{b}</b><span>{c}</span></div>' for a,b,c,_ in insight_items)
        st.markdown(f'<div class="insight-strip"><div class="insight-title">✦ KEY INSIGHTS</div>{cells}</div>',unsafe_allow_html=True)


    # Expanded performance intelligence: every tile is derived from closed alert records.
    performance_items = []
    if not valid.empty and "final_percent" in valid.columns:
        returns = pd.to_numeric(valid["final_percent"], errors="coerce").dropna()
        if not returns.empty:
            performance_items.append(("AVERAGE RETURN", f"{returns.mean():+.2f}%", f"{len(returns)} closed alerts"))
            best_trade = valid.loc[pd.to_numeric(valid["final_percent"], errors="coerce").idxmax()]
            worst_trade = valid.loc[pd.to_numeric(valid["final_percent"], errors="coerce").idxmin()]
            performance_items.append(("BIGGEST WINNER", str(best_trade.get("symbol", "Unknown")), f'{float(best_trade["final_percent"]):+.2f}% return'))
            performance_items.append(("BIGGEST LOSER", str(worst_trade.get("symbol", "Unknown")), f'{float(worst_trade["final_percent"]):+.2f}% return'))

        if "peak_percent" in valid.columns:
            peaks = pd.to_numeric(valid["peak_percent"], errors="coerce").dropna()
            if not peaks.empty:
                peak_idx = pd.to_numeric(valid["peak_percent"], errors="coerce").idxmax()
                peak_row = valid.loc[peak_idx]
                performance_items.append(("BEST PEAK MOVE", str(peak_row.get("symbol", "Unknown")), f'{float(peak_row["peak_percent"]):+.2f}% peak'))

        if {"peak_percent", "final_percent"}.issubset(valid.columns):
            peak_values = pd.to_numeric(valid["peak_percent"], errors="coerce")
            final_values = pd.to_numeric(valid["final_percent"], errors="coerce")
            giveback_count = int(((peak_values >= 1.0) & (final_values < 0)).sum())
            performance_items.append(("PROFIT GIVEBACK", f"{giveback_count}", "Reached +1% peak, closed negative"))

        if {"signal_score", "final_percent"}.issubset(valid.columns):
            score_data = pd.DataFrame({
                "score": pd.to_numeric(valid["signal_score"], errors="coerce"),
                "return": pd.to_numeric(valid["final_percent"], errors="coerce")
            }).dropna()
            if len(score_data) >= 5 and score_data["score"].nunique() > 1 and score_data["return"].nunique() > 1:
                score_corr = score_data["score"].corr(score_data["return"])
                if pd.notna(score_corr):
                    relation = "Positive" if score_corr >= 0.35 else ("Negative" if score_corr <= -0.35 else "No clear relationship")
                    performance_items.append(("SCORE / RETURN LINK", relation, f"Correlation {score_corr:+.2f} · n={len(score_data)}"))

    detector_perf = detector_summary(valid)
    if not detector_perf.empty:
        eligible_detectors = detector_perf[detector_perf["alerts"] >= 2]
        if not eligible_detectors.empty:
            top_detector = eligible_detectors.sort_values(["avg_return", "alerts"], ascending=[False, False]).iloc[0]
            performance_items.append(("BEST DETECTOR", str(top_detector["detector"]), f'{top_detector["avg_return"]:+.2f}% avg · n={int(top_detector["alerts"])}'))

    if not symbol_rank.empty:
        consistent = symbol_rank[symbol_rank["signals"] >= 3].copy()
        consistent = consistent[consistent["decisive"] > 0]
        if not consistent.empty:
            consistent = consistent.sort_values(["win_rate", "signals"], ascending=[False, False])
            row = consistent.iloc[0]
            performance_items.append(("MOST CONSISTENT COIN", str(row["symbol"]), f'{row["win_rate"]:.1f}% decisive win · n={int(row["signals"])}'))

    if performance_items:
        st.markdown('<div class="insight-strip"><div class="insight-title">✦ PERFORMANCE INTELLIGENCE</div></div>', unsafe_allow_html=True)
        performance_cards = "".join(
            f'<div class="performance-insight"><small>{label}</small><b>{value}</b><span>{detail}</span></div>'
            for label, value, detail in performance_items
        )
        st.markdown(
            """<style>
            .performance-insight-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:-18px}
            .performance-insight{display:flex;flex-direction:column;justify-content:center;min-width:0;min-height:104px;padding:13px 15px;border:1px solid rgba(22,177,238,.30);border-radius:12px;background:linear-gradient(145deg,rgba(8,34,56,.96),rgba(3,15,29,.98))}
            .performance-insight small{font-size:.62rem;letter-spacing:.10em;color:#8daec5;font-weight:900}
            .performance-insight b{font-size:1.12rem;color:#f2f8ff;margin:7px 0 4px;overflow-wrap:anywhere}
            .performance-insight span{font-size:.72rem;color:#39e75f;overflow-wrap:anywhere}
            @media(max-width:760px){.performance-insight-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.performance-insight{padding:11px;min-height:96px}.performance-insight b{font-size:1rem}}
            </style><div class="performance-insight-grid">""" + performance_cards + "</div>",
            unsafe_allow_html=True
        )
    else:
        st.info("Performance intelligence will appear as closed alert records accumulate.")

    st.caption("Win = final return ≥ +1%; loss = ≤ −0.5%; neutral = between those thresholds. Decisive win rate excludes neutral outcomes. Figures use current loaded R2 archive records.")
if active_page == "Patterns":
    st.header("Pattern intelligence")
    st.caption("Explore what separates successful and unsuccessful signals. Use these findings to evaluate Pingr improvements; no scanner rules are changed here.")

    # Enrich outcome records with detector labels from the corresponding alert record
    # only when the outcome stream does not already contain a usable detector field.
    pattern_data = classified.copy()
    detector_candidates = ["detector", "alert_type", "signal_type", "strategy"]
    detector_field = next((name for name in detector_candidates if name in pattern_data.columns), None)
    if detector_field is None and not alerts.empty and {"alert_id", "detector"}.issubset(alerts.columns) and "alert_id" in pattern_data.columns:
        detector_map = alerts.dropna(subset=["alert_id"]).drop_duplicates("alert_id", keep="last")[["alert_id", "detector"]]
        pattern_data = pattern_data.merge(detector_map, on="alert_id", how="left", validate="many_to_one")
        detector_field = "detector"

    if detector_field:
        pattern_data["_pattern_type"] = pattern_data[detector_field].fillna("").astype(str).str.lower().map(
            lambda value: "pullback" if "pullback" in value else "normal"
        )
        pullback_data = pattern_data[pattern_data["_pattern_type"].eq("pullback")].copy()
        normal_data = pattern_data[pattern_data["_pattern_type"].eq("normal")].copy()
    else:
        pullback_data = pd.DataFrame()
        normal_data = pd.DataFrame()

    def render_pattern_analysis(frame, mode):
        if frame.empty:
            if mode == "pullback":
                st.info("No Pullback outcome records could be identified in the current archive. The Pullback tab needs a detector/type label on the outcome or matching alert record.")
            elif mode == "normal":
                st.info("No classifiable normal-alert outcome records are available.")
            else:
                st.info("No usable winner/loser outcome records are available in the current archive.")
            return

        frame = frame[frame["result"].astype(str).str.lower().isin(["win", "loss", "neutral"])].copy()
        if frame.empty:
            st.info("No classified outcomes are available for this group.")
            return

        wins_here = int(frame["result"].astype(str).str.lower().eq("win").sum())
        losses_here = int(frame["result"].astype(str).str.lower().eq("loss").sum())
        neutral_here = int(frame["result"].astype(str).str.lower().eq("neutral").sum())
        metric_row([
            ("Evaluated alerts", f"{len(frame):,}"),
            ("Winners", f"{wins_here:,}"),
            ("Losers", f"{losses_here:,}"),
            ("Neutral", f"{neutral_here:,}"),
            ("Decisive win rate", f"{wins_here / (wins_here + losses_here) * 100:.1f}%" if wins_here + losses_here else "—"),
        ])

        # Explicit score calibration: show how each recorded original score band
        # distributes across wins, losses and neutral outcomes.
        st.subheader("Signal score breakdown")
        score_field = next((field for field in ["original_score", "signal_score"] if field in frame.columns), None)
        if score_field:
            score_values = pd.to_numeric(frame[score_field], errors="coerce")
            score_bands = [
                ("≤8", lambda x: x <= 8), ("9–10", lambda x: 9 <= x <= 10),
                ("11–12", lambda x: 11 <= x <= 12), ("13–16", lambda x: 13 <= x <= 16),
                ("17+", lambda x: x >= 17),
            ]
            score_rows = []
            for band_label, band_test in score_bands:
                band = frame[score_values.notna() & score_values.map(band_test)]
                band_result = band["result"].astype(str).str.lower()
                w = int(band_result.eq("win").sum())
                l = int(band_result.eq("loss").sum())
                n = int(band_result.eq("neutral").sum())
                score_rows.append({
                    "Score band": band_label, "Alerts": len(band),
                    "Wins": w, "Losses": l, "Neutral": n,
                    "Decisive win rate": f"{w / (w + l) * 100:.1f}%" if w + l else "—",
                })
            st.dataframe(pd.DataFrame(score_rows), use_container_width=True, hide_index=True)
            st.caption("Uses the score recorded with each evaluated alert. Bands are descriptive, not recommended thresholds.")
            scored_losses = frame[frame["result"].astype(str).str.lower().eq("loss")].copy()
            scored_losses["_score_numeric"] = pd.to_numeric(scored_losses[score_field], errors="coerce")
            if not scored_losses.empty:
                loss_score = scored_losses["_score_numeric"].dropna()
                if not loss_score.empty:
                    st.metric("Losing alerts with a recorded score", f"{len(loss_score):,}",
                              help=f"Median losing-alert score: {loss_score.median():.1f}")
        else:
            st.info("No recorded signal-score field is available in this outcome group. The dashboard will not infer scores.")

        # Surface the symbols behind losing outcomes rather than only showing
        # aggregate winner/loser indicator medians.
        st.subheader("Losing symbols")
        if "symbol" in frame.columns:
            losing = frame[frame["result"].astype(str).str.lower().eq("loss")].copy()
            if not losing.empty:
                losing["_pnl_numeric"] = pd.to_numeric(
                    losing["pnl_percent"] if "pnl_percent" in losing else pd.Series(index=losing.index, dtype="float64"),
                    errors="coerce",
                )
                losing["_score_numeric"] = pd.to_numeric(
                    losing[score_field] if score_field else pd.Series(index=losing.index, dtype="float64"),
                    errors="coerce",
                )
                losing["symbol"] = losing["symbol"].fillna("Unknown").astype(str)
                loss_symbols = losing.groupby("symbol", dropna=False).agg(
                    Losses=("result", "size"),
                    **{"Average loss %": ("_pnl_numeric", "mean"),
                       "Median loss %": ("_pnl_numeric", "median"),
                       "Median score": ("_score_numeric", "median")},
                ).reset_index().rename(columns={"symbol": "Symbol"})
                loss_symbols = loss_symbols.sort_values(
                    ["Losses", "Average loss %"], ascending=[False, True], na_position="last"
                )
                loss_symbols["Average loss %"] = loss_symbols["Average loss %"].map(
                    lambda x: f"{x:+.2f}%" if pd.notna(x) else "—"
                )
                loss_symbols["Median loss %"] = loss_symbols["Median loss %"].map(
                    lambda x: f"{x:+.2f}%" if pd.notna(x) else "—"
                )
                loss_symbols["Median score"] = loss_symbols["Median score"].map(
                    lambda x: f"{x:.1f}" if pd.notna(x) else "—"
                )
                st.dataframe(loss_symbols, use_container_width=True, hide_index=True)
                st.caption("Ranked by number of losing evaluated alerts. Repeated losses on one symbol are shown as counts; this is not a prediction.")
            else:
                st.info("No losing symbol outcomes are recorded in this group.")
        else:
            st.info("Symbol is not recorded on these outcome rows, so losing symbols cannot be listed.")

        specs = list(pattern_specs)
        if mode == "pullback":
            # Add Pullback-specific outcome/management measures only when recorded.
            for field, label, kind in [
                ("mfe_percent", "Maximum favourable excursion", "percent"),
                ("mae_percent", "Maximum adverse excursion", "percent"),
                ("pnl_percent", "Recorded P&L", "percent"),
                ("dist_ma20", "Distance from MA20", "percent"),
                ("pullback", "Pullback depth", "number"),
            ]:
                if field in frame.columns and all(existing[0] != field for existing in specs):
                    specs.append((field, label, kind))

        def display_value(value, kind):
            if pd.isna(value):
                return "—"
            if kind == "volume":
                return compact_volume(value)
            if kind == "percent":
                return f"{value:+.2f}%"
            if kind == "multiple":
                return f"{value:.2f}×"
            return f"{value:.1f}"

        cards, findings = [], []
        for field, label, kind in specs:
            if field not in frame.columns:
                continue
            groups = {}
            all_values = []
            for outcome_name in ("win", "loss"):
                vals = pd.to_numeric(frame.loc[frame["result"].astype(str).str.lower().eq(outcome_name), field], errors="coerce").dropna()
                if not vals.empty:
                    if kind == "volume":
                        groups[outcome_name] = {"minimum": vals.min(), "maximum": vals.max(), "n": len(vals)}
                    else:
                        q1, med, q3 = vals.quantile([.25, .50, .75]).tolist()
                        groups[outcome_name] = {"q1": q1, "median": med, "q3": q3, "n": len(vals)}
                    all_values.extend(vals.tolist())
                else:
                    groups[outcome_name] = None
            if not all_values:
                continue

            sides = []
            for outcome_name, heading, tone in [("win", "WINNERS", "win"), ("loss", "LOSERS", "loss")]:
                stats = groups[outcome_name]
                if stats is None:
                    sides.append(f'<div class="pattern-side {tone}"><b>{heading}</b><div class="pattern-no-data">No recorded values</div></div>')
                else:
                    if kind == "volume":
                        main_value = f'Min {display_value(stats["minimum"], kind)} · Max {display_value(stats["maximum"], kind)}'
                        range_value = ""
                    else:
                        main_value = display_value(stats["median"], kind)
                        range_value = f'<div class="pattern-range">{display_value(stats["q1"], kind)} – {display_value(stats["q3"], kind)} <span>· IQR</span></div>'
                    sides.append(
                        f'<div class="pattern-side {tone}"><div class="pattern-side-top"><span class="pattern-side-label">{heading}</span>'
                        f'<span class="pattern-n">n={stats["n"]}</span></div><div class="pattern-median">{main_value}</div>'
                        f'{range_value}</div>'
                    )
            card_tag = "MIN · MAX" if kind == "volume" else "MEDIAN · IQR"
            cards.append(
                '<div class="pattern-card"><div class="pattern-card-head"><span>' + label +
                f'</span><span class="pattern-card-tag">{card_tag}</span></div><div class="pattern-compare">' +
                ''.join(sides) + '</div></div>'
            )
            if groups["win"] and groups["loss"] and kind != "volume":
                findings.append((label, kind, groups["win"], groups["loss"]))

        st.subheader("Winning vs losing conditions")
        if cards:
            st.markdown(
                """<style>
                .pattern-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
                .pattern-card{border:1px solid rgba(71,157,199,.30);border-radius:15px;padding:14px;background:linear-gradient(145deg,rgba(9,31,49,.96),rgba(4,17,31,.98));min-width:0}
                .pattern-card-head{display:flex;justify-content:space-between;gap:8px;margin-bottom:12px}
                .pattern-card-head>span:first-child{font-size:.95rem;font-weight:850;color:#eef7ff}
                .pattern-card-tag{font-size:.58rem;color:#8ca9bf;letter-spacing:.07em}
                .pattern-compare{display:grid;grid-template-columns:1fr 1fr;gap:9px}
                .pattern-side{border-radius:11px;padding:10px;min-width:0;background:rgba(255,255,255,.025)}
                .pattern-side.win{border:1px solid rgba(57,231,145,.20)}
                .pattern-side.loss{border:1px solid rgba(255,91,99,.20)}
                .pattern-side-top{display:flex;justify-content:space-between;gap:5px}
                .pattern-side-label{font-size:.61rem;letter-spacing:.09em;font-weight:900}
                .win .pattern-side-label{color:#75e4ac}.loss .pattern-side-label{color:#ff929b}
                .pattern-n{font-size:.61rem;color:#819bb0}
                .pattern-median{font-size:1.25rem;font-weight:900;color:#f4f9ff;margin-top:6px}
                .pattern-range{font-size:.68rem;color:#a8bfd1;margin-top:3px}
                .pattern-range span{color:#718ca2;font-size:.61rem}
                .pattern-no-data{font-size:.78rem;color:#8299ad;padding:12px 0}
                @media(max-width:760px){.pattern-grid{grid-template-columns:1fr}.pattern-card{padding:12px}}
                </style><div class="pattern-grid">""" + "".join(cards) + "</div>",
                unsafe_allow_html=True
            )
        else:
            st.info("No supported numeric winner/loser indicator fields are available for this group.")

        st.subheader("Recommendations")
        st.caption("Evidence-led investigation suggestions only. Differences are descriptive, not proof of causation.")
        recommendations = []
        for label, kind, win_stats, loss_stats in findings:
            wn, ln = win_stats["n"], loss_stats["n"]
            if min(wn, ln) < 10:
                recommendations.append((1, label, f"Collect more evidence for {label}: only {wn} winning and {ln} losing records have usable values. No rule change is justified yet."))
                continue
            wmed, lmed = win_stats["median"], loss_stats["median"]
            if pd.isclose(wmed, lmed):
                recommendations.append((2, label, f"{label} medians are similar for winners and losers. It is not separating outcomes clearly in this sample."))
            elif wmed > lmed:
                recommendations.append((0, label, f"Winners have a higher median {label} ({display_value(wmed, kind)} vs {display_value(lmed, kind)}). Investigate this as a possible confirmation feature; validate on future alerts."))
            else:
                recommendations.append((0, label, f"Winners have a lower median {label} ({display_value(wmed, kind)} vs {display_value(lmed, kind)}). Investigate whether lower readings are associated with better outcomes; validate on future alerts."))
        if recommendations:
            for _, label, message in sorted(recommendations, key=lambda item: (item[0], item[1]))[:6]:
                st.markdown(f"**{label}** — {message}")
        else:
            st.info("There are not yet enough paired winner/loser indicator observations to generate recommendations.")
        if min(wins_here, losses_here) < 10:
            st.warning(f"Small sample: {wins_here} winners and {losses_here} losers. Treat these comparisons as exploratory.")
        else:
            st.caption("Use later, unseen alerts to check whether these patterns persist before considering scanner changes.")

        if mode == "pullback":
            st.subheader("Pullback evidence")
            st.caption("Pullback-specific fields are displayed only when present in the archived records. Detection and confirmation stages are not inferred from outcome alone.")
            stage_fields = [field for field in ["pullback_stage", "stage", "confirmed", "is_confirmed", "confirmation_status"] if field in frame.columns]
            if stage_fields:
                for field in stage_fields:
                    st.write(f"Recorded {field}: {frame[field].fillna('Unknown').astype(str).value_counts().to_dict()}")
            else:
                st.info("No explicit Pullback detected/confirmed stage field was found in these outcome records.")

    tab_all, tab_normal, tab_pullback = st.tabs(["Consolidated", "Normal Alerts", "Pullback"])
    with tab_all:
        st.caption("All classified alert outcomes, including Pullback. The breakdown below uses the recorded detector label for each alert.")
        render_pattern_analysis(pattern_data, "all")

        st.subheader("Consolidated results by alert type")
        if detector_field and not pattern_data.empty:
            by_type = pattern_data.copy()
            by_type["_result"] = by_type["result"].astype(str).str.lower()
            by_type["_detector_label"] = by_type[detector_field].fillna("Unknown").astype(str).str.strip()
            by_type.loc[by_type["_detector_label"].eq(""), "_detector_label"] = "Unknown"
            rows = []
            for detector_name, group in by_type.groupby("_detector_label", dropna=False):
                w = int(group["_result"].eq("win").sum())
                l = int(group["_result"].eq("loss").sum())
                n = int(group["_result"].eq("neutral").sum())
                row = {
                    "Alert type": detector_name,
                    "Evaluated": len(group),
                    "Wins": w,
                    "Losses": l,
                    "Neutral": n,
                    "Decisive win rate": f"{w / (w + l) * 100:.1f}%" if w + l else "—",
                }
                if "pnl_percent" in group:
                    pnl = pd.to_numeric(group["pnl_percent"], errors="coerce")
                    row["Average P&L"] = f"{pnl.mean():+.2f}%" if pnl.notna().any() else "—"
                    row["Median P&L"] = f"{pnl.median():+.2f}%" if pnl.notna().any() else "—"
                rows.append(row)
            if rows:
                st.dataframe(pd.DataFrame(rows).sort_values("Evaluated", ascending=False), use_container_width=True, hide_index=True)
                st.caption("Decisive win rate excludes neutral outcomes. Small alert-type samples are descriptive only.")
                st.subheader("Patterns within each alert type")
                for detector_name, group in by_type.groupby("_detector_label", dropna=False):
                    with st.expander(f"{detector_name} · {len(group)} evaluated alerts"):
                        render_pattern_analysis(group, "type")
            else:
                st.info("No detector-labelled outcome groups are available.")
        else:
            st.warning("The consolidated outcome patterns are available, but a reliable detector label could not be matched to these outcome IDs. Alert-type comparisons are withheld rather than guessed.")
    with tab_normal:
        st.caption("All classified alerts except records explicitly labelled Pullback.")
        if detector_field:
            render_pattern_analysis(normal_data, "normal")
        else:
            st.warning("Cannot safely separate normal alerts from Pullback because the archived outcomes do not contain a detector label and no matching alert-record mapping was available.")
    with tab_pullback:
        st.caption("Only records explicitly labelled Pullback; no other detector is included.")
        if detector_field:
            render_pattern_analysis(pullback_data, "pullback")
        else:
            st.warning("Cannot safely identify Pullback outcomes because the archived outcomes do not contain a detector label and no matching alert-record mapping was available.")

if active_page == "Scanner intelligence":
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
        st.info("No separate scanner/diagnostic event types were found in the loaded R2 archives.")

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

if active_page == "Detector performance":
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
                     color="avg_return", color_continuous_scale=["#ff5b63", "#315b7a", "#39e75f"],
                     labels={"avg_return": "Average final return", "detector": ""})
        fig.update_layout(template="plotly_dark", height=max(220, 65 * len(chart)),
                          margin=dict(l=8, r=12, t=8, b=8), paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False,
                          font=dict(color="#edf5ff"))
        fig.update_traces(textposition="outside", cliponaxis=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No closed tracked-alert returns are available yet. Scanner skips and diagnostics are excluded from detector performance.")

if active_page == "Coin intelligence":
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

if active_page == "Signal quality":
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

if active_page == "Logs & diagnostics":
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
