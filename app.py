import streamlit as st
import pandas as pd
import plotly.express as px
import json
import hashlib
import io

from datetime import datetime

# =====================================================
# PINGR ANALYTICS DASHBOARD
# Version 1.0
# =====================================================

st.set_page_config(
    page_title="Pingr Analytics",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background-color: #0b1020;
    color: #e5e7eb;
}
[data-testid="stMetric"] {
    background: #151d30;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #27344d;
}
h1, h2, h3 {
    color: #e5e7eb;
}
</style>
""", unsafe_allow_html=True)


# =====================================================
# HEADER
# =====================================================

st.title("📊 PINGR ANALYTICS")
st.caption("Alert intelligence • Performance analysis • Historical tracking")

st.divider()


# =====================================================
# FILE UPLOAD
# =====================================================

st.sidebar.header("Log Management")

uploaded_files = st.sidebar.file_uploader(
    "Upload Pingr JSONL logs",
    type=None,
    accept_multiple_files=True
)

st.sidebar.info(
    "Upload one or more Pingr alert logs. "
    "Records are combined and duplicate lines are removed."
)


# =====================================================
# PARSING
# =====================================================

def parse_logs(files):

    records = []
    seen = set()
    errors = 0

    for file in files:

        content = file.getvalue().decode(
            "utf-8", errors="replace"
        )

        for line_number, line in enumerate(content.splitlines(), 1):

            if not line.strip():
                continue

            try:
                record = json.loads(line)

                if not isinstance(record, dict):
                    errors += 1
                    continue

                fingerprint = hashlib.sha256(
                    json.dumps(
                        record,
                        sort_keys=True,
                        default=str
                    ).encode()
                ).hexdigest()

                if fingerprint in seen:
                    continue

                seen.add(fingerprint)

                record["_source_file"] = file.name
                record["_line_number"] = line_number

                records.append(record)

            except Exception:
                errors += 1

    return records, errors


# =====================================================
# FIELD HELPERS
# =====================================================

def first_value(record, names):

    for name in names:
        value = record.get(name)

        if value is not None:
            return value

    return None


def number(value):

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def normalise_records(records):

    rows = []

    for record in records:

        row = dict(record)

        row["_event"] = first_value(
            record,
            ["event", "event_type", "type", "action"]
        )

        row["_alert_type"] = first_value(
            record,
            [
                "alert_type",
                "signal_type",
                "setup_type",
                "strategy",
                "detector"
            ]
        )

        row["_symbol"] = first_value(
            record,
            ["symbol", "pair", "ticker"]
        )

        row["_score"] = number(first_value(
            record,
            ["score", "signal_score", "alert_score"]
        ))

        row["_volume_24h"] = number(first_value(
            record,
            [
                "volume_24h_usdt",
                "min_24h_volume",
                "volume24h",
                "quote_volume_24h",
                "traded_volume_24h"
            ]
        ))

        row["_vol_ratio"] = number(first_value(
            record,
            ["vol_ratio", "volume_ratio"]
        ))

        row["_rsi14"] = number(first_value(
            record,
            ["rsi14", "rsi_14", "rsi"]
        ))

        row["_rsi6"] = number(first_value(
            record,
            ["rsi6", "rsi_6"]
        ))

        row["_atr"] = number(first_value(
            record,
            ["atr_pct", "atr"]
        ))

        row["_final_return"] = number(first_value(
            record,
            [
                "final_pct",
                "final_return",
                "return_pct",
                "final_change_pct"
            ]
        ))

        row["_peak_return"] = number(first_value(
            record,
            [
                "peak_pct",
                "peak_return",
                "mfe_pct",
                "max_favourable_excursion"
            ]
        ))

        row["_worst_return"] = number(first_value(
            record,
            [
                "worst_pct",
                "worst_return",
                "mae_pct",
                "max_adverse_excursion"
            ]
        ))

        row["_pullback_depth"] = number(first_value(
            record,
            ["pullback_depth", "depth", "pullback_pct"]
        ))

        row["_run24"] = number(first_value(
            record,
            ["run24", "run_24h", "change24"]
        ))

        rows.append(row)

    return pd.DataFrame(rows)


# =====================================================
# MAIN DASHBOARD
# =====================================================

if not uploaded_files:

    st.info("Upload your Pingr JSONL logs to begin.")

    st.markdown("""
    ### Dashboard modules

    - Overall alert performance
    - Momentum analysis
    - Pullback analysis
    - Volume intelligence
    - RSI and MACD analysis
    - BTC market conditions
    - Historical performance
    - Score effectiveness
    """)

    st.stop()


records, parsing_errors = parse_logs(uploaded_files)

if not records:
    st.error("No valid JSON records were found.")
    st.stop()

df = normalise_records(records)


# =====================================================
# OVERVIEW
# =====================================================

st.header("1. Overall Overview")

total_records = len(df)

events = (
    df["_event"]
    .fillna("Unclassified")
    .astype(str)
)

event_counts = events.value_counts()

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Records", total_records)

c2.metric(
    "Alert Outcomes",
    int((events == "alert_outcome").sum())
)

c3.metric(
    "Momentum Events",
    int(events.str.contains("momentum", case=False).sum())
)

c4.metric("Parsing Errors", parsing_errors)


# =====================================================
# EVENT BREAKDOWN
# =====================================================

st.subheader("Event Breakdown")

event_df = event_counts.reset_index()
event_df.columns = ["Event", "Count"]

st.plotly_chart(
    px.bar(
        event_df,
        x="Event",
        y="Count",
        title="Records by Event Type",
        template="plotly_dark"
    ),
    use_container_width=True
)


# =====================================================
# ALERT TYPES
# =====================================================

st.header("2. Alert Types")

alert_types = (
    df["_alert_type"]
    .fillna("Unknown")
    .astype(str)
    .value_counts()
)

st.dataframe(
    alert_types.rename("Count"),
    use_container_width=True
)


# =====================================================
# OUTCOME ANALYSIS
# =====================================================

st.header("3. Performance Analysis")

outcomes = df[
    events.eq("alert_outcome")
].copy()

if not outcomes.empty:

    valid_returns = outcomes[
        outcomes["_final_return"].notna()
    ].copy()

    if not valid_returns.empty:

        winners = valid_returns[
            valid_returns["_final_return"] > 0
        ]

        losers = valid_returns[
            valid_returns["_final_return"] < 0
        ]

        flats = valid_returns[
            valid_returns["_final_return"] == 0
        ]

        win_rate = (
            len(winners) / len(valid_returns) * 100
        )

        a, b, c, d = st.columns(4)

        a.metric("Tracked Outcomes", len(valid_returns))
        b.metric("Winners", len(winners))
        c.metric("Losers", len(losers))
        d.metric("Win Rate", f"{win_rate:.1f}%")

        st.metric(
            "Average Final Return",
            f"{valid_returns['_final_return'].mean():.2f}%"
        )

        st.metric(
            "Average Peak Return",
            (
                f"{valid_returns['_peak_return'].mean():.2f}%"
                if valid_returns["_peak_return"].notna().any()
                else "Not available"
            )
        )

        st.metric(
            "Average Worst Movement",
            (
                f"{valid_returns['_worst_return'].mean():.2f}%"
                if valid_returns["_worst_return"].notna().any()
                else "Not available"
            )
        )

        st.plotly_chart(
            px.histogram(
                valid_returns,
                x="_final_return",
                color_discrete_sequence=["#00cc96"],
                title="Distribution of Final Returns",
                template="plotly_dark"
            ),
            use_container_width=True
        )

        st.dataframe(
            valid_returns[
                [
                    "_symbol",
                    "_alert_type",
                    "_score",
                    "_final_return",
                    "_peak_return",
                    "_worst_return"
                ]
            ],
            use_container_width=True
        )

    else:
        st.warning(
            "Outcome records were found, but recognised final-return "
            "fields were not available. Field mapping needs verification."
        )

else:
    st.warning("No alert_outcome records found in this upload.")


# =====================================================
# MOMENTUM ANALYSIS
# =====================================================

st.header("4. Momentum Analysis")

momentum = df[
    df["_alert_type"]
    .fillna("")
    .astype(str)
    .str.contains("momentum", case=False)
].copy()

if not momentum.empty:

    st.metric("Momentum Records", len(momentum))

    scored = momentum[
        momentum["_score"].notna()
    ]

    if not scored.empty:

        st.subheader("Momentum Score Distribution")

        st.plotly_chart(
            px.histogram(
                scored,
                x="_score",
                nbins=15,
                title="Momentum Scores",
                template="plotly_dark"
            ),
            use_container_width=True
        )

    else:
        st.info("No recognised Momentum score fields found.")

    st.subheader("Momentum Records")

    st.dataframe(
        momentum,
        use_container_width=True
    )

else:
    st.info("No Momentum records identified.")


# =====================================================
# SCORE VS PERFORMANCE
# =====================================================

st.header("5. Score Effectiveness")

if not outcomes.empty:

    score_data = outcomes[
        outcomes["_score"].notna()
        & outcomes["_final_return"].notna()
    ].copy()

    if len(score_data) >= 3:

        st.plotly_chart(
            px.scatter(
                score_data,
                x="_score",
                y="_final_return",
                hover_data=["_symbol"],
                trendline="ols",
                title="Original Score vs Final Return",
                template="plotly_dark"
            ),
            use_container_width=True
        )

        correlation = score_data[
            ["_score", "_final_return"]
        ].corr().iloc[0, 1]

        st.metric(
            "Score / Return Correlation",
            f"{correlation:.3f}"
        )

        st.caption(
            "Correlation is descriptive, not proof that score "
            "causes better or worse performance."
        )

    else:
        st.info(
            "At least three matched score/outcome records "
            "are required for this chart."
        )


# =====================================================
# VOLUME ANALYSIS
# =====================================================

st.header("6. Volume Intelligence")

volume_data = df[
    df["_volume_24h"].notna()
    | df["_vol_ratio"].notna()
].copy()

if not volume_data.empty:

    v1, v2 = st.columns(2)

    with v1:

        st.subheader("24h Traded Volume")

        st.dataframe(
            volume_data[
                ["_symbol", "_volume_24h"]
            ],
            use_container_width=True
        )

    with v2:

        st.subheader("Tracked Volume Ratio")

        st.dataframe(
            volume_data[
                ["_symbol", "_vol_ratio"]
            ],
            use_container_width=True
        )

    st.caption(
        "Tracked vol_ratio is displayed separately from scanner "
        "5m volume spike multiples. They are not interchangeable."
    )

else:
    st.info("No recognised volume fields found.")


# =====================================================
# RSI AND ATR
# =====================================================

st.header("7. Technical Indicators")

indicator_data = df[
    df["_rsi14"].notna()
    | df["_rsi6"].notna()
    | df["_atr"].notna()
].copy()

if not indicator_data.empty:

    st.dataframe(
        indicator_data[
            [
                "_symbol",
                "_rsi14",
                "_rsi6",
                "_atr"
            ]
        ],
        use_container_width=True
    )

else:
    st.info("No recognised RSI or ATR fields found.")


# =====================================================
# PULLBACK ANALYSIS
# =====================================================

st.header("8. Pullback Deep Dive")

pullbacks = df[
    df["_alert_type"]
    .fillna("")
    .astype(str)
    .str.contains("pullback", case=False)
].copy()

if not pullbacks.empty:

    st.metric("Pullback Records", len(pullbacks))

    pullback_columns = [
        "_symbol",
        "_pullback_depth",
        "_run24",
        "_rsi14",
        "_rsi6",
        "_atr",
        "_vol_ratio",
        "_final_return",
        "_peak_return",
        "_worst_return"
    ]

    st.dataframe(
        pullbacks[
            [c for c in pullback_columns if c in pullbacks.columns]
        ],
        use_container_width=True
    )

    if (
        pullbacks["_pullback_depth"].notna().any()
        and pullbacks["_final_return"].notna().any()
    ):

        st.plotly_chart(
            px.scatter(
                pullbacks,
                x="_pullback_depth",
                y="_final_return",
                hover_data=["_symbol"],
                title="Pullback Depth vs Final Return",
                template="plotly_dark"
            ),
            use_container_width=True
        )

else:
    st.info("No Pullback records identified.")


# =====================================================
# RAW DATA
# =====================================================

st.header("9. Raw Log Explorer")

with st.expander("Inspect all parsed records"):

    st.dataframe(
        df,
        use_container_width=True
    )


# =====================================================
# DOWNLOAD
# =====================================================

st.header("10. Export")

csv_data = df.to_csv(index=False).encode("utf-8")

st.download_button(
    "Download Combined Dataset (CSV)",
    data=csv_data,
    file_name="pingr_combined_logs.csv",
    mime="text/csv"
)

json_data = "\n".join(
    json.dumps(record, default=str)
    for record in records
)

st.download_button(
    "Download Combined Dataset (JSONL)",
    data=json_data,
    file_name="pingr_combined_logs.jsonl",
    mime="application/json"
)


# =====================================================
# FOOTER
# =====================================================

st.divider()

st.caption(
    "PINGR ANALYTICS v1.0 | "
    "Analytical tool only — does not modify Pingr."
)

st.caption(
    "Results depend on the fields present in uploaded logs. "
    "Unmatched alert and outcome records must not be treated as trades."
)
