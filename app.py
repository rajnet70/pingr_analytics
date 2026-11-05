import streamlit as st
import pandas as pd
import plotly.express as px
import json
import hashlib
from io import BytesIO

st.set_page_config(page_title="Pingr Analytics", page_icon="📊", layout="wide")

st.markdown("""
<style>
:root {
  --bg: #080d18;
  --panel: #101a2b;
  --panel2: #142238;
  --line: rgba(148, 163, 184, .16);
  --muted: #91a1b8;
  --text: #edf3fb;
  --cyan: #67d5e8;
  --green: #42d6a4;
  --red: #ff7185;
}
.stApp {
  background:
    radial-gradient(ellipse at 12% 0%, rgba(37, 99, 145, .17), transparent 34%),
    radial-gradient(ellipse at 90% 8%, rgba(38, 76, 125, .12), transparent 28%),
    var(--bg);
  color: var(--text);
}
.block-container {max-width: 1480px; padding-top: 2rem; padding-bottom: 3rem;}
[data-testid="stHeader"] {background: rgba(8,13,24,.82);}
[data-testid="stSidebar"] {background: #0b1422; border-right: 1px solid var(--line);}
[data-testid="stMetric"] {
  background: linear-gradient(145deg, rgba(20,34,56,.98), rgba(13,24,40,.98));
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 18px 18px 15px;
  box-shadow: 0 10px 30px rgba(0,0,0,.13);
}
[data-testid="stMetricLabel"] {color: var(--muted); font-size: .82rem; letter-spacing: .04em;}
[data-testid="stMetricValue"] {color: var(--text); font-weight: 700; letter-spacing: -.035em;}
h1, h2, h3 {letter-spacing: -.035em;}
h1 {font-size: 2.35rem !important; font-weight: 750 !important;}
h2 {font-size: 1.35rem !important; margin-top: 1.4rem !important;}
h3 {font-size: 1.02rem !important;}
.pingr-eyebrow {color: var(--cyan); text-transform: uppercase; letter-spacing: .18em; font-size: .72rem; font-weight: 700;}
.pingr-subtitle {color: var(--muted); font-size: .98rem; margin-top: -.55rem;}
.pingr-rule {height: 1px; background: linear-gradient(90deg, rgba(103,213,232,.55), rgba(148,163,184,.04)); margin: 1rem 0 1.4rem;}
.pingr-card {
  background: linear-gradient(145deg, rgba(19,32,52,.96), rgba(12,22,37,.96));
  border: 1px solid var(--line); border-radius: 16px;
  padding: 17px 19px; margin: 5px 0 12px;
}
.pingr-muted {color: var(--muted); font-size: .84rem;}
div[data-testid="stExpander"] {border: 1px solid var(--line); border-radius: 14px; background: rgba(15,26,43,.58);}
.stTabs [data-baseweb="tab-list"] {gap: 8px; border-bottom: 1px solid var(--line);}
.stTabs [data-baseweb="tab"] {background: transparent; border-radius: 9px 9px 0 0; padding: 10px 16px;}
.stButton button, .stDownloadButton button {border-radius: 10px; border: 1px solid var(--line);}
[data-testid="stDataFrame"] {border: 1px solid var(--line); border-radius: 12px; overflow: hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="pingr-eyebrow">Market intelligence workspace</div>', unsafe_allow_html=True)
st.title("PINGR <span style='color:#67d5e8'>ANALYTICS</span>", anchor=False)
st.markdown('<div class="pingr-subtitle">Detector performance · Historical patterns · Signal quality</div><div class="pingr-rule"></div>', unsafe_allow_html=True)

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
    out = a.groupby("detector", dropna=False).agg(
        alerts=("final_percent", "size"),
        wins=("final_percent", lambda x: int((x > 0).sum())),
        avg_return=("final_percent", "mean"),
    ).reset_index()
    out["win_rate"] = out.wins / out.alerts * 100
    return out


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
            show = perf_log[["detector", "alerts", "win_rate", "avg_return"]].copy()
            show["win_rate"] = show.win_rate.map(lambda x: f"{x:.0f}%")
            show["avg_return"] = show.avg_return.map(lambda x: f"{x:+.2f}%")
            show.columns = ["Detector", "Alerts", "Win rate", "Avg return"]
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
    show = perf_all[["detector", "alerts", "win_rate", "avg_return"]].copy()
    show["win_rate"] = show.win_rate.map(lambda x: f"{x:.1f}%")
    show["avg_return"] = show.avg_return.map(lambda x: f"{x:+.2f}%")
    show.columns = ["Detector", "Alerts", "Win rate", "Average return"]
    st.dataframe(show, use_container_width=True, hide_index=True)
    chart_df = perf_all.sort_values("avg_return", ascending=True).copy()
    fig = px.bar(
        chart_df, x="avg_return", y="detector", orientation="h",
        text=chart_df["avg_return"].map(lambda x: f"{x:+.2f}%"),
        color="avg_return", color_continuous_scale=["#ff7185", "#263b58", "#42d6a4"],
        labels={"avg_return": "Average final return", "detector": ""}
    )
    fig.update_layout(
        template="plotly_dark", height=270, margin=dict(l=8, r=12, t=12, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        coloraxis_showscale=False, xaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,.12)", zeroline=True, zerolinecolor="rgba(226,232,240,.5)"),
        yaxis=dict(showgrid=False), font=dict(color="#dce7f5")
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
else:
    st.info("No final tracked alert outcomes available.")

# Small operational pulse
st.markdown('<div class="pingr-eyebrow">05 / Scanner telemetry</div>', unsafe_allow_html=True)
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
st.caption("PINGR ANALYTICS • Synopsis and pattern tracker • No changes are made to Pingr.")
