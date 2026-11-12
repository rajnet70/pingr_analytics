import streamlit as st
import pandas as pd
import plotly.express as px
import json
import hashlib
from io import BytesIO

st.set_page_config(page_title="Pingr Analytics", page_icon="📊", layout="wide")

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
st.markdown('<div class="pingr-subtitle">Trading intelligence · Detector performance · Historical patterns</div><div class="pingr-rule"></div>', unsafe_allow_html=True)

st.sidebar.header("Log Management")
uploads = st.sidebar.file_uploader(
    "Upload one or more Pingr JSONL logs", type=None, accept_multiple_files=True,
    help="Upload multiple dated logs together to compare patterns across them."
)
st.sidebar.caption("For now, historical comparisons use the files uploaded together. Permanent storage is a later step.")


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
    generic = df[df.event_type.eq("generic")].copy()
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
    st.info("Upload one or more Pingr JSONL logs to generate a synopsis and compare patterns.")
    st.markdown("**Designed for quick decisions:** latest-log synopsis, detector health, recurring patterns and optional diagnostics.")
    st.stop()

per_file, combined_rows, errors, duplicate_count = parse_files(uploads)
if not combined_rows:
    st.error("No valid JSON objects found. Check that each line contains one JSON object.")
    st.stop()

combined, alerts, outcomes, generic = prepare(combined_rows)
valid = alerts.dropna(subset=["final_percent"]).copy() if not alerts.empty and "final_percent" in alerts else pd.DataFrame()

# Main glance view
st.markdown('<div class="pingr-eyebrow">01 / Performance overview</div>', unsafe_allow_html=True)
st.header("At a glance")
win_rate = (valid.final_percent.gt(0).mean() * 100) if not valid.empty else 0
avg_return = valid.final_percent.mean() if not valid.empty else float("nan")
metric_row([
    ("Tracked alerts", f"{len(valid):,}"),
    ("Win rate", f"{win_rate:.1f}%" if not valid.empty else "—"),
    ("Average return", f"{avg_return:+.2f}%" if not valid.empty else "—"),
    ("Logs loaded", f"{len(per_file):,}"),
])
st.caption(f"{len(combined):,} unique records • {duplicate_count:,} duplicate records skipped • {len(errors):,} parse errors")

# Graph-first overview: compact detector mix and return distribution.
if not valid.empty:
    overview_left, overview_right = st.columns(2)
    with overview_left:
        detector_mix = valid["detector"].value_counts().rename_axis("Detector").reset_index(name="Alerts")
        mix_fig = px.pie(detector_mix, names="Detector", values="Alerts", hole=.68,
                         color_discrete_sequence=["#20d6a0", "#8b5cf6", "#22d3ee", "#fb7185"])
        mix_fig.update_layout(template="plotly_dark", height=235, margin=dict(l=5,r=5,t=8,b=5),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font=dict(color="#edf5ff"), legend=dict(orientation="h",y=-.12))
        mix_fig.add_annotation(text=f"{len(valid)}<br>alerts",x=.5,y=.5,showarrow=False,
                               font=dict(size=17,color="#edf5ff"))
        st.plotly_chart(mix_fig,use_container_width=True,config={"displayModeBar":False})
    with overview_right:
        return_values = valid["final_percent"].dropna()
        return_fig = px.histogram(pd.DataFrame({"Final return (%)":return_values}),
                                  x="Final return (%)",nbins=14,
                                  color_discrete_sequence=["#22d3ee"])
        return_fig.update_layout(template="plotly_dark",height=235,margin=dict(l=8,r=8,t=8,b=8),
                                 paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                                 font=dict(color="#edf5ff"),showlegend=False,
                                 xaxis_title="Final return (%)",yaxis_title="Alert count")
        st.plotly_chart(return_fig,use_container_width=True,config={"displayModeBar":False})


st.markdown('<div class="pingr-eyebrow">02 / Recent activity</div>', unsafe_allow_html=True)
st.header("Log intelligence")
latest_name = list(per_file.keys())[-1]
for filename, rows in per_file.items():
    log_df, log_alerts, log_outcomes, log_generic = prepare(rows)
    log_valid = log_alerts.dropna(subset=["final_percent"]).copy() if not log_alerts.empty and "final_percent" in log_alerts else pd.DataFrame()
    log_win = log_valid.final_percent.gt(0).mean() * 100 if not log_valid.empty else 0
    log_avg = log_valid.final_percent.mean() if not log_valid.empty else float("nan")
    with st.expander(("LATEST · " if filename == latest_name else "LOG · ") + filename, expanded=(filename == latest_name)):
        metric_row([
            ("Records", f"{len(log_df):,}"),
            ("Closed alerts", f"{len(log_valid):,}"),
            ("Win rate", f"{log_win:.1f}%" if not log_valid.empty else "—"),
            ("Average return", f"{log_avg:+.2f}%" if not log_valid.empty else "—"),
        ])
        perf_log = detector_summary(log_valid)
        if not perf_log.empty:
            st.markdown("**Detector snapshot**")
            show = perf_log[["detector", "alerts", "wins", "losses", "neutral", "win_rate", "avg_return", "median_return"]].copy()
            show["win_rate"] = show.win_rate.map(lambda x: f"{x:.1f}%")
            show["avg_return"] = show.avg_return.map(lambda x: f"{x:+.2f}%")
            show["median_return"] = show.median_return.map(lambda x: f"{x:+.2f}%")
            show.columns = ["Detector", "Alerts", "Wins", "Losses", "Neutral", "Decisive win rate", "Avg return", "Median return"]
            st.dataframe(show, use_container_width=True, hide_index=True)
        notes = synopsis_observations(log_valid, log_generic)
        st.markdown("**What stood out**")
        if notes:
            for kind, note in notes:
                if kind == "warn": st.warning(note)
                elif kind == "good": st.success(note)
                else: st.info(note)
        else:
            st.info("Not enough closed-alert data to generate observations yet.")

# Historical comparisons across files
st.markdown('<div class="pingr-eyebrow">03 / Cross-log learning</div>', unsafe_allow_html=True)
st.header("Historical patterns")
if len(per_file) < 2:
    st.info("Upload at least two logs together to compare recurring patterns. This first version does not permanently store logs.")
else:
    hist_rows = []
    for filename, rows in per_file.items():
        _, a, _, _ = prepare(rows)
        p = detector_summary(a)
        if not p.empty:
            for _, r in p.iterrows():
                hist_rows.append({"log": filename, "detector": r.detector, "alerts": int(r.alerts), "avg_return": r.avg_return, "win_rate": r.win_rate})
    hist = pd.DataFrame(hist_rows)
    if not hist.empty:
        recurring = hist.groupby("detector").agg(
            logs_seen=("log", "nunique"),
            total_alerts=("alerts", "sum"),
            avg_return=("avg_return", "mean"),
            negative_logs=("avg_return", lambda x: int((x < 0).sum())),
        ).reset_index()
        recurring["pattern"] = recurring.apply(
            lambda r: "Recurring underperformance" if r.negative_logs >= 2 else ("Mixed results" if r.logs_seen >= 2 else "Single-log observation"), axis=1
        )
        st.dataframe(recurring.round(2), use_container_width=True, hide_index=True)
        st.caption("Historical average = equal-weighted mean of each log's detector average. Recurring underperformance requires negative log-level averages in at least two separate logs. Detector Health below uses an alert-weighted average across all tracked alerts.")
    else:
        st.info("No comparable tracked-alert outcomes found across these files.")

# Compact detector health across all uploaded logs
st.markdown('<div class="pingr-eyebrow">04 / Detector performance</div>', unsafe_allow_html=True)
st.header("Detector health")
perf_all = detector_summary(valid)
if not perf_all.empty:
    show = perf_all[["detector", "alerts", "wins", "losses", "neutral", "win_rate", "avg_return", "median_return"]].copy()
    show["win_rate"] = show.win_rate.map(lambda x: f"{x:.1f}%")
    show["avg_return"] = show.avg_return.map(lambda x: f"{x:+.2f}%")
    show["median_return"] = show.median_return.map(lambda x: f"{x:+.2f}%")
    show.columns = ["Detector", "Alerts", "Wins", "Losses", "Neutral", "Decisive win rate", "Average return", "Median return"]
    st.dataframe(show, use_container_width=True, hide_index=True)
    chart_df = perf_all.sort_values("avg_return", ascending=True).copy()
    fig = px.bar(
        chart_df, x="avg_return", y="detector", orientation="h",
        text=chart_df["avg_return"].map(lambda x: f"{x:+.2f}%"),
        color="avg_return", color_continuous_scale=["#ff7185", "#263b58", "#42d6a4"],
        labels={"avg_return": "Average final return", "detector": ""}
    )
    fig.update_layout(
        template="plotly_dark", height=245, margin=dict(l=8, r=12, t=8, b=6),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        coloraxis_showscale=False, xaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,.12)", zeroline=True, zerolinecolor="rgba(226,232,240,.5)"),
        yaxis=dict(showgrid=False), font=dict(color="#dce7f5")
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
else:
    st.info("No final tracked alert outcomes available.")

# Analyse alert_outcome records separately; never join them to alert_record rows.
render_outcome_intelligence(outcomes)

# Small operational pulse
st.markdown('<div class="pingr-eyebrow">06 / Scanner telemetry</div>', unsafe_allow_html=True)
st.header("Scanner activity")
if not generic.empty:
    sent = generic.get("alert_sent", pd.Series(False, index=generic.index)).fillna(False).astype(bool).sum()
    spike5 = ncol(generic, "volume_spike_5m").mean()
    spike15 = ncol(generic, "volume_spike_15m").mean()
    metric_row([
        ("Scanner snapshots", f"{len(generic):,}"),
        ("Alert-sent markers", f"{int(sent):,}"),
        ("Avg 5m volume spike", f"{spike5:.2f}x" if pd.notna(spike5) else "—"),
        ("Avg 15m volume spike", f"{spike15:.2f}x" if pd.notna(spike15) else "—"),
    ])
    if pd.notna(spike5) and pd.notna(spike15):
        scanner_fig = px.bar(
            pd.DataFrame({"Timeframe": ["5-minute", "15-minute"], "Average spike": [spike5, spike15]}),
            x="Timeframe", y="Average spike", text_auto=".2f",
            color="Timeframe", color_discrete_sequence=["#67d5e8", "#6689c7"]
        )
        scanner_fig.update_layout(
            template="plotly_dark", height=220, margin=dict(l=8, r=8, t=10, b=8),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, font=dict(color="#dce7f5"),
            yaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,.12)", title="Average volume spike (x)"),
            xaxis=dict(showgrid=False)
        )
        st.plotly_chart(scanner_fig, use_container_width=True, config={"displayModeBar": False})

with st.expander("Advanced diagnostics — open only when investigating a pattern"):
    st.subheader("Tracked alert ledger")
    if not alerts.empty:
        cols = [c for c in ["symbol", "detector", "alert_time", "signal_score", "label", "final_percent", "peak_percent", "worst_percent", "exit_reason", "rsi_14", "rsi_6", "atr_pct", "vol_ratio", "taker_buy_ratio", "macd_5m", "macd_15m", "macd_1h", "btc_1h", "btc_4h", "btc_above_ma50_1h"] if c in alerts]
        st.dataframe(alerts[cols], use_container_width=True, hide_index=True)
    st.subheader("Momentum diagnostics")
    mom = alerts[alerts.detector.eq("Momentum")] if not alerts.empty else pd.DataFrame()
    if not mom.empty:
        mcols = [c for c in ["symbol", "signal_score", "final_percent", "peak_percent", "worst_percent", "rsi_14", "rsi_6", "atr_pct", "vol_ratio", "taker_buy_ratio", "macd_5m", "macd_15m", "macd_1h", "btc_1h", "btc_4h"] if c in mom]
        st.dataframe(mom[mcols], use_container_width=True, hide_index=True)
    st.subheader("Pullback diagnostics")
    pb = alerts[alerts.detector.eq("Pullback")] if not alerts.empty else pd.DataFrame()
    if not pb.empty:
        pcols = [c for c in ["symbol", "pullback", "run24", "dist_ma20", "rsi_14", "atr_pct", "vol_ratio", "taker_buy_ratio", "peak_percent", "worst_percent", "final_percent", "exit_reason"] if c in pb]
        st.dataframe(pb[pcols], use_container_width=True, hide_index=True)
    st.subheader("Timeframe outcome summary")
    if not outcomes.empty:
        for c in ["pnl_percent", "mfe_percent", "mae_percent"]:
            outcomes[c] = pd.to_numeric(outcomes.get(c), errors="coerce")
        if "timeframe" in outcomes:
            tf = outcomes.groupby("timeframe", dropna=False).agg(
                evaluations=("alert_id", "count"), unique_alerts=("alert_id", "nunique"),
                avg_pnl=("pnl_percent", "mean"), avg_mfe=("mfe_percent", "mean"), avg_mae=("mae_percent", "mean")
            ).reset_index()
            st.dataframe(tf.round(3), use_container_width=True, hide_index=True)
            st.caption("Timeframe evaluations are not separate tracked alerts.")
    st.subheader("Raw event inventory")
    counts = combined.event_type.value_counts().rename_axis("Event type").reset_index(name="Records")
    st.dataframe(counts, use_container_width=True, hide_index=True)
    if errors:
        st.subheader("Parse errors")
        st.dataframe(pd.DataFrame(errors), use_container_width=True, hide_index=True)

st.markdown('<div class="pingr-eyebrow">06 / Data access</div>', unsafe_allow_html=True)
st.header("Export & data")
parsed_csv = combined.to_csv(index=False).encode("utf-8")
st.download_button("Download parsed records (CSV)", parsed_csv, "pingr_parsed_records.csv", "text/csv")
jsonl_out = "\n".join(json.dumps(r, default=str) for r in combined_rows)
st.download_button("Download deduplicated records (JSONL)", jsonl_out, "pingr_deduplicated.jsonl", "application/json")

st.divider()
st.caption("PINGR ANALYTICS • Signal intelligence and detector diagnostics • Dashboard-only analysis; no changes are made to Pingr engine or configuration.")
