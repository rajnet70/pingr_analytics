import streamlit as st
import pandas as pd
import plotly.express as px
import json
import hashlib
from io import BytesIO
import os
import base64
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Pingr Analytics", page_icon="📊", layout="wide")

# Poll the archive branch automatically; cached Git blobs prevent repeat downloads.
st_autorefresh(interval=120000, key="pingr_archive_auto_refresh")

st.markdown("""
<style>
:root{--bg:#070c16;--panel:#0d1929;--line:rgba(130,160,190,.18);--muted:#91a4bb;--text:#edf5ff;--cyan:#22d3ee;--green:#20d6a0;--red:#fb7185}
.stApp{background:radial-gradient(ellipse at 12% 0%,rgba(20,120,160,.13),transparent 32%),radial-gradient(ellipse at 92% 8%,rgba(52,75,150,.12),transparent 28%),var(--bg);color:var(--text)}
.block-container{max-width:1600px;padding:1rem 1.2rem 2rem}
[data-testid="stHeader"]{background:rgba(7,12,22,.88)}
[data-testid="stSidebar"]{background:#091321;border-right:1px solid var(--line)}
h1,h2,h3{letter-spacing:-.035em}
.pingr-title{font-size:clamp(1.65rem,3vw,2.35rem);font-weight:800;letter-spacing:-.055em;margin:.1rem 0 .15rem;color:var(--text)}
.pingr-title span{color:var(--cyan)}
.pingr-eyebrow{color:var(--cyan);text-transform:uppercase;letter-spacing:.16em;font-size:.68rem;font-weight:800;margin-top:.3rem}
.pingr-subtitle{color:var(--muted);font-size:.88rem;margin:.15rem 0 .6rem}
.pingr-rule{height:1px;background:linear-gradient(90deg,rgba(34,211,238,.55),rgba(148,163,184,.03));margin:.55rem 0 .9rem}
h2{font-size:1.15rem!important;margin:.45rem 0 .55rem!important}
h3{font-size:.98rem!important}
[data-testid="stMetric"]{background:linear-gradient(145deg,rgba(18,36,58,.98),rgba(10,23,39,.98));border:1px solid var(--line);border-radius:13px;padding:11px 13px;box-shadow:0 8px 24px rgba(0,0,0,.12);min-height:88px}
[data-testid="stMetricLabel"]{color:var(--muted);font-size:.76rem;letter-spacing:.025em}
[data-testid="stMetricValue"]{color:var(--text);font-weight:800;font-size:1.55rem;letter-spacing:-.04em}
div[data-testid="stExpander"]{border:1px solid var(--line);border-radius:12px;background:rgba(13,25,41,.68)}
.stButton button,.stDownloadButton button{border-radius:9px;border:1px solid var(--line);min-height:40px}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:10px;overflow:hidden}
[data-testid="stPlotlyChart"]{border:1px solid rgba(130,160,190,.12);border-radius:12px;background:rgba(10,22,37,.4);padding:3px}
@media(max-width:900px){.block-container{padding:.75rem .75rem 1.5rem}.pingr-title{font-size:1.65rem}[data-testid="stMetric"]{padding:9px 10px;min-height:80px}[data-testid="stMetricValue"]{font-size:1.25rem}}
@media(max-width:600px){.block-container{padding:.55rem .55rem 1.25rem}.pingr-title{font-size:1.45rem}[data-testid="stMetricLabel"]{font-size:.69rem}[data-testid="stMetricValue"]{font-size:1.1rem}}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="pingr-eyebrow">Market intelligence workspace</div>', unsafe_allow_html=True)
st.markdown('<h1 class="pingr-title">PINGR <span>ANALYTICS</span></h1>', unsafe_allow_html=True)
st.markdown('<div class="pingr-subtitle">Live GitHub archive · Trading intelligence · Detector performance · Historical patterns</div><div class="pingr-rule"></div>', unsafe_allow_html=True)


class ArchiveUpload(BytesIO):
    def __init__(self, name, content):
        super().__init__(content)
        self.name = name

# Read the private archive branch directly from GitHub.
GITHUB_OWNER = "rajnet70"
GITHUB_REPO = "Binance-discord-alert"
GITHUB_BRANCH = "pingr-log-archive"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"

def github_headers():
    token = st.secrets.get("GITHUB_TOKEN")
    if not token:
        github_section = st.secrets.get("github", {})
        token = github_section.get("token") if hasattr(github_section, "get") else None
    if not token:
        raise RuntimeError(
            "GitHub read token is not configured in Streamlit Secrets. "
            "Add GITHUB_TOKEN there (read-only Contents access to the private archive repository)."
        )
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

@st.cache_data(ttl=60, show_spinner=False)
def github_archive_index():
    # Use the branch's recursive Git tree instead of Contents directory listing.
    # The Contents endpoint does not provide reliable page traversal for this use.
    headers = github_headers()
    branch_response = requests.get(
        f"{GITHUB_API}/branches/{GITHUB_BRANCH}",
        headers=headers,
        timeout=30
    )
    branch_response.raise_for_status()
    branch_data = branch_response.json()
    tree_sha = branch_data["commit"]["commit"]["tree"]["sha"]

    tree_response = requests.get(
        f"{GITHUB_API}/git/trees/{tree_sha}",
        params={"recursive": "1"},
        headers=headers,
        timeout=60
    )
    tree_response.raise_for_status()
    tree_data = tree_response.json()
    if tree_data.get("truncated"):
        raise RuntimeError("GitHub returned a truncated archive tree; refusing to load an incomplete archive.")

    return [
        {
            "name": item["path"].rsplit("/", 1)[-1],
            "path": item["path"],
            "sha": item["sha"],
            "size": item.get("size", 0)
        }
        for item in tree_data.get("tree", [])
        if item.get("type") == "blob"
        and "/" not in item.get("path", "")
        and item.get("path", "").startswith("pingr-archive__")
        and not item.get("path", "").endswith(".sync.json")
    ]

@st.cache_data(ttl=3600, max_entries=1000, show_spinner=False)
def github_archive_file(path, sha):
    response = requests.get(
        f"{GITHUB_API}/contents/{requests.utils.quote(path, safe='/')}",
        params={"ref": GITHUB_BRANCH},
        headers=github_headers(),
        timeout=(15, 120)
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("sha") != sha:
        raise RuntimeError(f"Archive file changed while loading: {path}")
    if payload.get("encoding") != "base64":
        raise RuntimeError(f"Unexpected GitHub content encoding for {path}")
    return base64.b64decode(payload["content"])

def load_archive():
    objects = github_archive_index()
    loaded, errors = [], []
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = {
            pool.submit(github_archive_file, item["path"], item["sha"]): item
            for item in objects
        }
        for job in as_completed(jobs):
            item = jobs[job]
            try:
                content = job.result()
                if content:
                    name = item["name"].replace("pingr-archive__", "", 1)
                    loaded.append((name, content))
            except Exception as exc:
                errors.append(f'{item["path"]}: {type(exc).__name__}: {exc}')

    loaded.sort(key=lambda x: x[0])
    latest = max((item["name"] for item in objects), default="Not available")
    return loaded, {
        "files": len(objects),
        "loaded": len(loaded),
        "errors": errors,
        "updated": latest,
        "last_sync": None,
    }

st.sidebar.header("Live GitHub archive")
st.sidebar.caption("Source: rajnet70/Binance-discord-alert · branch: pingr-log-archive")
if st.sidebar.button("Refresh archive now", use_container_width=True):
    st.cache_data.clear()
try:
    with st.spinner("Reading Pingr logs from the private GitHub archive…"):
        archive_files, archive_status = load_archive()
except Exception as exc:
    st.error(f"Could not read the GitHub archive: {type(exc).__name__}: {exc}")
    st.stop()
uploads = [ArchiveUpload(name, content) for name, content in archive_files]
st.sidebar.metric("Archive files loaded", f'{archive_status["loaded"]:,}')
st.sidebar.caption(f'Latest GitHub archive file: {archive_status["updated"]}')
if archive_status["errors"]:
    with st.sidebar.expander(f'{len(archive_status["errors"])} archive file(s) could not be read'):
        st.write(archive_status["errors"])
else:
    st.sidebar.success("GitHub archive read completed without file errors.")
st.sidebar.caption("GitHub archive index refresh: 60 seconds. Archive files are cached by file SHA.")

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
    st.warning("No readable JSONL log files were found on the archive branch yet.")
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

# Display only the latest six-hour data window, anchored to the newest event
# actually present in the archive (not the GitHub upload/sync timestamp).
latest_event_ts = combined["_ts"].max()
if pd.isna(latest_event_ts):
    st.error("The archive contains no parseable event timestamps; cannot determine the latest six-hour session.")
    st.stop()
session_end = latest_event_ts
session_start = session_end - pd.Timedelta(hours=6)
session_mask = combined["_ts"].between(session_start, session_end, inclusive="both")
session_frame = combined.loc[session_mask].drop(columns=["_ts"], errors="ignore")
combined, alerts, outcomes, generic = prepare(session_frame.to_dict("records"))
if not combined.empty and "timestamp" in combined.columns:
    combined["_ts"] = pd.to_datetime(combined["timestamp"], errors="coerce", utc=True)
else:
    combined["_ts"] = pd.NaT
if not alerts.empty and "timestamp" in alerts.columns:
    alerts["_ts"] = pd.to_datetime(alerts["timestamp"], errors="coerce", utc=True)
if not outcomes.empty and "timestamp" in outcomes.columns:
    outcomes["_ts"] = pd.to_datetime(outcomes["timestamp"], errors="coerce", utc=True)
valid = alerts.dropna(subset=["final_percent"]).copy() if not alerts.empty and "final_percent" in alerts else pd.DataFrame()
session_start_pak = session_start.tz_convert("Asia/Karachi").strftime("%d %b %Y · %I:%M %p PKT")
session_end_pak = session_end.tz_convert("Asia/Karachi").strftime("%d %b %Y · %I:%M %p PKT")
session_age_hours = (pd.Timestamp.now(tz="UTC") - session_end).total_seconds() / 3600
session_source_files = session_frame["_source_file"].nunique() if "_source_file" in session_frame else 0

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
st.markdown('<div class="pingr-subtitle">Latest six-hour session · Detector results · Coin intelligence · Recent activity</div><div class="pingr-rule"></div>', unsafe_allow_html=True)

# Keep the archive controls compact and out of the main analysis.
st.sidebar.header("Data connection")
st.sidebar.caption("Private GitHub archive · pingr-log-archive")
st.sidebar.metric("Log files loaded", f'{archive_status["loaded"]:,}')
st.sidebar.caption(f'Newest file in archive: {archive_status["updated"]}')
if st.sidebar.button("Refresh latest data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
if archive_status["errors"]:
    with st.sidebar.expander(f'{len(archive_status["errors"])} file read errors'):
        st.write(archive_status["errors"])
st.sidebar.caption("Auto-refresh: every 2 minutes")

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
latest_alert_label = latest_alert_time.tz_convert("Asia/Karachi").strftime("%d %b · %I:%M %p PKT") if pd.notna(latest_alert_time) else "No alert records"
metric_row([
    ("Closed tracked alerts", f"{closed_count:,}"),
    ("Wins / losses / neutral", f"{wins:,} / {losses:,} / {neutral:,}"),
    ("Decisive win rate", f"{decisive_rate:.1f}%" if decisive else "—"),
    ("Average final return", f"{avg_return:+.2f}%" if pd.notna(avg_return) else "—"),
])
st.caption(f'Latest alert record: {latest_alert_label} · {len(combined):,} unique events across {archive_status["loaded"]:,} archived files · {duplicate_count:,} duplicate rows removed')

# 2. Detector performance
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

# 3. Coin intelligence
st.header("Coin intelligence")
coin_source = valid.copy() if not valid.empty and "symbol" in valid else pd.DataFrame()
if not coin_source.empty:
    coin_source["final_percent"] = pd.to_numeric(coin_source["final_percent"], errors="coerce")
    coin_source = coin_source.dropna(subset=["symbol", "final_percent"])
    coin_rank = coin_source.groupby("symbol").agg(
        alerts=("final_percent", "size"),
        avg_return=("final_percent", "mean"),
        median_return=("final_percent", "median"),
        wins=("final_percent", lambda x: int((x >= 1.0).sum()))
    ).reset_index()
    coin_rank = coin_rank[coin_rank["alerts"] >= 2]
    if not coin_rank.empty:
        coin_rank["win_rate"] = coin_rank["wins"] / coin_rank["alerts"] * 100
        left, right = st.columns(2)
        with left:
            st.subheader("Strongest coins")
            st.dataframe(coin_rank.sort_values("avg_return", ascending=False).head(8).round(2),
                         use_container_width=True, hide_index=True)
        with right:
            st.subheader("Weakest coins")
            st.dataframe(coin_rank.sort_values("avg_return", ascending=True).head(8).round(2),
                         use_container_width=True, hide_index=True)
        st.caption("Closed tracked alerts only · minimum two observations per coin.")
    else:
        st.info("Not enough closed-alert observations per coin to rank reliably.")
else:
    st.info("Coin rankings will appear when closed tracked-alert records include symbol and final return.")

# 4. Signal quality — use the dedicated outcome stream, keeping it separate from alert_record.
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
        st.dataframe(latest_eval[["symbol", "result"] + quality_cols].sort_values(
            "pnl_percent", ascending=False) if "pnl_percent" in quality_cols and "symbol" in latest_eval else latest_eval[["result"] + quality_cols],
            use_container_width=True, hide_index=True)
    st.caption("Latest evaluation per alert ID. Outcome records are analyzed separately and are not merged with detector alert records.")
else:
    st.info("No usable alert_outcome records with alert IDs are present in the archive yet.")

# 5. Latest six-hour session — all analytics above are scoped to this window.
st.header("Latest session · last 6 hours of available Pingr data")
st.caption(f"Session window: {session_start_pak} → {session_end_pak} · anchored to the newest actual event timestamp, not archive sync time.")
if session_age_hours > 12:
    st.error(f"ARCHIVE DATA IS STALE · Newest event is {session_age_hours:.1f} hours old. This shows the latest available data, not proof of current Pingr activity.")
else:
    st.success(f"Newest available event is {session_age_hours:.1f} hours old.")
metric_row([
    ("Events in 6-hour window", f"{len(combined):,}"),
    ("Unique symbols", f'{combined["symbol"].nunique() if "symbol" in combined else 0:,}'),
    ("Source files contributing", f"{session_source_files:,}"),
    ("Actual alert records", f'{len(alerts):,}'),
])
session_event_counts = combined.get("event_type", pd.Series(dtype="object")).fillna("unknown").value_counts()
if not session_event_counts.empty:
    st.caption("Session event mix: " + " · ".join(f"{k}: {v:,}" for k, v in session_event_counts.items()))

st.subheader("Latest activity · 50 most recent events")
if not combined.empty and "_ts" in combined:
    latest_activity = combined.sort_values("_ts", ascending=False, na_position="last").head(50).copy()
    useful = latest_activity[
        ~latest_activity.get("event_type", pd.Series("", index=latest_activity.index)).astype(str).isin(
            ["volume_cache_snapshot", "signal_quality_snapshot"]
        )
    ]
    cols = [c for c in ["timestamp", "symbol", "event_type", "alert_type", "signal_score", "final_percent", "diagnostic.stage", "diagnostic.reason"] if c in latest_activity]
    if cols:
        st.dataframe(latest_activity[cols], use_container_width=True, hide_index=True)
    else:
        st.info("The latest session has records, but none of the standard activity fields are present.")
else:
    st.info("No timestamped activity is available in the latest session.")

# Recent actual alerts, capped to 20 rows.
st.header("Recent alerts · latest session")
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
