import streamlit as st
import pandas as pd
import plotly.express as px
import json
import hashlib
from io import BytesIO

st.set_page_config(page_title="Pingr Analytics", page_icon="📊", layout="wide")

st.markdown("""
<style>
.stApp {background:#0b1020;color:#e7edf7}
[data-testid="stMetric"] {background:#151f33;border:1px solid #2a3954;padding:14px;border-radius:12px}
</style>
""", unsafe_allow_html=True)

st.title("📊 PINGR ANALYTICS")
st.caption("Pingr log intelligence • Tracked outcomes • Momentum & Pullback research")

st.sidebar.header("Log Management")
uploads = st.sidebar.file_uploader(
    "Upload Pingr JSONL logs",
    type=None,
    accept_multiple_files=True,
    help="Select .jsonl or .txt log files. The parser reads one JSON object per line."
)

def parse_uploads(files):
    rows, seen, errors = [], set(), []
    for f in files or []:
        raw = f.getvalue().decode("utf-8-sig", errors="replace")
        for line_no, line in enumerate(raw.splitlines(), 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    raise ValueError("JSON line is not an object")
                fp = hashlib.sha256(
                    json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()
                ).hexdigest()
                if fp in seen:
                    continue
                seen.add(fp)
                obj["_source_file"] = f.name
                obj["_line"] = line_no
                rows.append(obj)
            except Exception as exc:
                errors.append({"file": f.name, "line": line_no, "error": str(exc)})
    return rows, errors

def numeric(series):
    return pd.to_numeric(series, errors="coerce")

def safe_df(rows):
    return pd.json_normalize(rows, sep=".")

def show_metric_row(items):
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)

if not uploads:
    st.info("Upload one or more Pingr JSONL files to begin.")
    st.markdown("""
    **Analysis modules**
    - Event inventory and alert counts
    - Final tracked alert outcomes (one row per alert record)
    - Separate 5m / 15m / 30m outcome evaluations
    - Momentum score and technical-condition analysis
    - Pullback depth, run-up, MA20, ATR and candle structure
    - Scanner volume spikes versus tracked `vol_ratio`
    - BTC direction and MACD alignment
    """)
    st.stop()

records, errors = parse_uploads(uploads)
if not records:
    st.error("No valid JSON objects found. Check that the file is JSONL (one JSON object per line).")
    st.stop()

raw = safe_df(records)
event = raw.get("event_type", pd.Series(["unknown"] * len(raw))).fillna("unknown").astype(str)
raw["event_type"] = event

# Preserve event families as separate datasets. Do not count generic snapshots as trades.
alert_records = raw[raw.event_type.eq("alert_record")].copy()
outcomes = raw[raw.event_type.eq("alert_outcome")].copy()
generic = raw[raw.event_type.eq("generic")].copy()
setup = raw[raw.event_type.eq("setup_alert")].copy()
continues = raw[raw.event_type.eq("momentum_continue")].copy()
ends = raw[raw.event_type.eq("momentum_end")].copy()

st.success(f"Loaded {len(records):,} unique JSON records from {len(uploads)} file(s).")
st.caption(f"Duplicate lines skipped: {sum(1 for _ in [])} • Parse errors: {len(errors)}")

st.header("1. Log overview")
show_metric_row([
    ("Total records", f"{len(raw):,}"),
    ("Tracked alert records", f"{len(alert_records):,}"),
    ("Outcome evaluations", f"{len(outcomes):,}"),
    ("Generic scanner snapshots", f"{len(generic):,}"),
])
event_counts = raw.event_type.value_counts().rename_axis("Event type").reset_index(name="Records")
c1, c2 = st.columns([1, 1])
with c1:
    st.dataframe(event_counts, use_container_width=True, hide_index=True)
with c2:
    st.plotly_chart(px.bar(event_counts, x="Event type", y="Records", template="plotly_dark",
                           title="Records by event type"), use_container_width=True)

if errors:
    with st.expander(f"Parsing errors ({len(errors)})"):
        st.dataframe(pd.DataFrame(errors), use_container_width=True)

# Helper to add typed numeric columns only when present.
def numcol(df, source, target=None):
    target = target or source
    if source in df.columns:
        df[target] = numeric(df[source])
    else:
        df[target] = pd.NA
    return df

# Tracked alert records are the canonical final alert-performance rows in this log.
st.header("2. Final tracked alert performance")
if alert_records.empty:
    st.warning("No `alert_record` events found. This file may contain scanner events only.")
else:
    for col in ["final_percent", "peak_percent", "worst_percent", "signal_score",
                "rsi_14", "rsi_6", "atr_pct", "vol_ratio", "taker_buy_ratio",
                "btc_1h", "btc_4h", "pullback", "run24", "dist_ma20",
                "change_24h", "minutes_held", "minutes_to_first_1pct"]:
        numcol(alert_records, col)

    alert_records["detector"] = alert_records.get("detector", "Unknown").fillna("Unknown")
    alert_records["symbol"] = alert_records.get("symbol", "Unknown").fillna("Unknown")
    valid = alert_records[alert_records.final_percent.notna()].copy()
    if not valid.empty:
        wins = valid[valid.final_percent > 0]
        losses = valid[valid.final_percent < 0]
        flats = valid[valid.final_percent == 0]
        win_rate = len(wins) / len(valid) * 100
        show_metric_row([
            ("Closed tracked alerts", len(valid)),
            ("Winners", len(wins)),
            ("Losers", len(losses)),
            ("Win rate", f"{win_rate:.1f}%"),
            ("Average final return", f"{valid.final_percent.mean():+.2f}%"),
        ])
        st.caption("These are `alert_record` final outcomes. They are not multiplied by the separate timeframe outcome evaluations.")
        perf = valid.groupby("detector", dropna=False).agg(
            alerts=("symbol", "count"),
            winners=("final_percent", lambda x: int((x > 0).sum())),
            losers=("final_percent", lambda x: int((x < 0).sum())),
            avg_final_pct=("final_percent", "mean"),
            avg_peak_pct=("peak_percent", "mean"),
            avg_worst_pct=("worst_percent", "mean"),
        ).reset_index()
        perf["win_rate_pct"] = perf.winners / perf.alerts * 100
        st.subheader("Performance by detector")
        st.dataframe(perf.round(2), use_container_width=True, hide_index=True)
        st.plotly_chart(px.bar(valid, x="symbol", y="final_percent", color="detector",
                               hover_data=["signal_score", "peak_percent", "worst_percent"],
                               template="plotly_dark", title="Final tracked return by alert"),
                        use_container_width=True)
    else:
        st.warning("Tracked alert records exist, but `final_percent` is missing.")

    st.subheader("Tracked alert ledger")
    display_cols = [c for c in [
        "symbol", "detector", "alert_time", "signal_score", "label",
        "final_percent", "peak_percent", "worst_percent", "exit_reason",
        "rsi_14", "rsi_6", "atr_pct", "vol_ratio", "taker_buy_ratio",
        "macd_5m", "macd_15m", "macd_1h", "btc_1h", "btc_4h",
        "btc_above_ma50_1h"
    ] if c in alert_records.columns]
    st.dataframe(alert_records[display_cols], use_container_width=True, hide_index=True)

st.header("3. Momentum analysis")
mom = alert_records[alert_records.get("detector", pd.Series(index=alert_records.index, dtype=str)).eq("Momentum")].copy() if not alert_records.empty else pd.DataFrame()
if mom.empty:
    st.info("No Momentum `alert_record` rows found in this upload.")
else:
    mom["final_percent"] = numeric(mom["final_percent"])
    mom["signal_score"] = numeric(mom["signal_score"])
    show_metric_row([
        ("Momentum alerts", len(mom)),
        ("Average score", f"{mom.signal_score.mean():.1f}" if mom.signal_score.notna().any() else "n/a"),
        ("Average final return", f"{mom.final_percent.mean():+.2f}%" if mom.final_percent.notna().any() else "n/a"),
    ])
    st.subheader("Score versus final tracked return")
    plot = mom.dropna(subset=["signal_score", "final_percent"])
    if len(plot) >= 2:
        st.plotly_chart(px.scatter(plot, x="signal_score", y="final_percent", color="label",
                                   hover_data=["symbol", "peak_percent", "worst_percent"],
                                   template="plotly_dark", title="Momentum score vs final return"),
                        use_container_width=True)
        corr = plot[["signal_score", "final_percent"]].corr().iloc[0, 1]
        st.metric("Sample score / return correlation", f"{corr:.3f}")
        st.caption("Descriptive only. Small samples and market conditions can distort correlation.")
    else:
        st.info("Not enough Momentum alert records with both score and final return for a comparison.")

    st.subheader("Momentum technical profile")
    tech_cols = [c for c in ["symbol", "signal_score", "final_percent", "peak_percent",
                              "worst_percent", "rsi_14", "rsi_6", "atr_pct", "vol_ratio",
                              "taker_buy_ratio", "macd_5m", "macd_15m", "macd_1h",
                              "btc_1h", "btc_4h", "btc_above_ma50_1h"] if c in mom.columns]
    st.dataframe(mom[tech_cols], use_container_width=True, hide_index=True)

st.header("4. Pullback deep dive")
pb = alert_records[alert_records.get("detector", pd.Series(index=alert_records.index, dtype=str)).eq("Pullback")].copy() if not alert_records.empty else pd.DataFrame()
if pb.empty:
    st.info("No Pullback `alert_record` rows found in this upload.")
else:
    for col in ["pullback", "run24", "dist_ma20", "ma20", "rsi_14", "atr_pct",
                "vol_ratio", "taker_buy_ratio", "move_share_pct", "body_ratio",
                "upper_wick", "lower_wick", "consec_green", "final_percent",
                "peak_percent", "worst_percent"]:
        numcol(pb, col)
    show_metric_row([
        ("Pullback alerts", len(pb)),
        ("Average depth", f"{pb.pullback.mean():.2f}%" if pb.pullback.notna().any() else "n/a"),
        ("Average 24h run", f"{pb.run24.mean():.2f}%" if pb.run24.notna().any() else "n/a"),
        ("Average final return", f"{pb.final_percent.mean():+.2f}%" if pb.final_percent.notna().any() else "n/a"),
    ])
    pbcols = [c for c in ["symbol", "pullback", "run24", "dist_ma20", "rsi_14",
                           "atr_pct", "vol_ratio", "taker_buy_ratio", "move_share_pct",
                           "body_ratio", "upper_wick", "lower_wick", "consec_green",
                           "btc_1h", "btc_4h", "btc_above_ma50_1h",
                           "peak_percent", "worst_percent", "final_percent", "exit_reason"] if c in pb.columns]
    st.dataframe(pb[pbcols], use_container_width=True, hide_index=True)
    chart = pb.dropna(subset=["pullback", "final_percent"])
    if len(chart) >= 2:
        st.plotly_chart(px.scatter(chart, x="pullback", y="final_percent", color="symbol",
                                   hover_data=["run24", "atr_pct", "taker_buy_ratio"],
                                   template="plotly_dark", title="Pullback depth vs final return"),
                        use_container_width=True)

st.header("5. Separate timeframe outcome evaluations")
if outcomes.empty:
    st.info("No `alert_outcome` events found.")
else:
    for col in ["pnl_percent", "mfe_percent", "mae_percent", "original_score",
                "original_volume_5m", "original_volume_24h", "original_rsi_15m"]:
        numcol(outcomes, col)
    tf_summary = outcomes.groupby("timeframe", dropna=False).agg(
        evaluations=("alert_id", "count"),
        unique_alerts=("alert_id", "nunique"),
        avg_pnl_pct=("pnl_percent", "mean"),
        avg_mfe_pct=("mfe_percent", "mean"),
        avg_mae_pct=("mae_percent", "mean"),
    ).reset_index()
    st.dataframe(tf_summary.round(3), use_container_width=True, hide_index=True)
    st.caption("Each row here is a timeframe evaluation. The same alert can appear at 5m, 15m and 30m; do not add these rows to the tracked alert count.")
    st.subheader("Outcome evaluation detail")
    ocols = [c for c in ["alert_id", "symbol", "timeframe", "result", "pnl_percent",
                          "mfe_percent", "mae_percent", "original_score",
                          "original_volume_5m", "original_volume_24h",
                          "original_rsi_15m", "original_macd_5m",
                          "original_macd_15m", "original_macd_1h"] if c in outcomes.columns]
    st.dataframe(outcomes[ocols], use_container_width=True, hide_index=True)

st.header("6. Scanner snapshots and volume")
if not generic.empty:
    for col in ["signal_score", "price_change_5m", "price_change_15m",
                "volume_spike_5m", "volume_spike_15m", "heat_index",
                "rsi_5m", "rsi_15m"]:
        numcol(generic, col)
    show_metric_row([
        ("Generic snapshots", len(generic)),
        ("Marked alert_sent", int(generic.get("alert_sent", pd.Series(False, index=generic.index)).fillna(False).astype(bool).sum())),
        ("Average 5m spike", f"{generic.volume_spike_5m.mean():.2f}x" if generic.volume_spike_5m.notna().any() else "n/a"),
        ("Average 15m spike", f"{generic.volume_spike_15m.mean():.2f}x" if generic.volume_spike_15m.notna().any() else "n/a"),
    ])
    st.dataframe(generic[[c for c in ["timestamp", "symbol", "signal_score", "alert_type",
                                     "alert_sent", "price_change_5m", "volume_spike_5m",
                                     "price_change_15m", "volume_spike_15m", "heat_index",
                                     "rsi_5m", "rsi_15m", "macd_bullish_5m",
                                     "macd_bullish_15m", "macd_bullish_1h", "sr_event"]
                          if c in generic.columns]], use_container_width=True, hide_index=True)
else:
    st.info("No generic scanner snapshots in this upload.")

st.header("7. Setup alerts")
if not setup.empty:
    st.dataframe(setup[[c for c in ["timestamp", "symbol", "alert_type", "alert_sent",
                                    "rsi_15m", "meta.pullback", "meta.run24",
                                    "meta.dist_ma20", "meta.vol_ratio"]
                        if c in setup.columns]], use_container_width=True, hide_index=True)
else:
    st.info("No setup_alert events found.")

st.header("8. Export")
csv = raw.to_csv(index=False).encode("utf-8")
st.download_button("Download parsed records (CSV)", csv, "pingr_parsed_records.csv", "text/csv")
jsonl = "\n".join(json.dumps(r, default=str) for r in records)
st.download_button("Download deduplicated records (JSONL)", jsonl, "pingr_deduplicated.jsonl", "application/json")

st.divider()
st.caption("PINGR ANALYTICS • Parser aligned to observed Pingr JSONL event names and fields. No changes are made to Pingr.")
