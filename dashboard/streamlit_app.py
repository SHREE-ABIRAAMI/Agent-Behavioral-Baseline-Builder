import os
import sys

# Insert workspace root at index 0 of sys.path before any package imports
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import json
import math
import time
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

import app.database as database
import app.config as config

# Page Configuration
st.set_page_config(
    page_title="AB³ — Data Science & Analytics Console",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── HIGH-END CUSTOM GLASSMORPHISM & BRAND THEME STYLING ──────────────────────
def inject_custom_theme():
    st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&family=Outfit:wght@400;500;600;700;800&display=swap');

    :root {
        --bg-main: #0d0405;
        --bg-card: rgba(28, 10, 13, 0.85);
        --border-maroon: rgba(153, 27, 27, 0.45);
        --primary-red: #991b1b;
        --primary-glow: rgba(153, 27, 27, 0.5);
        --copper-gold: #d97706;
        --emerald-green: #10b981;
        --text-bright: #ffffff;
        --text-dim: #fecdd3;
        --text-muted: #a8a29e;
    }

    /* Global styling */
    .stApp {
        background: radial-gradient(circle at 50% 10%, #1f080b 0%, #0d0405 70%) !important;
        color: var(--text-bright) !important;
        font-family: 'Outfit', sans-serif !important;
    }

    h1, h2, h3, h4, .stMetric label, [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #120507 !important;
        border-right: 1px solid var(--border-maroon) !important;
    }

    /* Custom Header Box */
    .hero-banner {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(135deg, rgba(40, 12, 17, 0.95) 0%, rgba(13, 4, 5, 0.98) 100%);
        border: 1px solid var(--border-maroon);
        border-radius: 18px;
        padding: 24px 32px;
        margin-bottom: 28px;
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.7), inset 0 0 15px rgba(153, 27, 27, 0.15);
    }

    .hero-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 30px;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: var(--text-bright);
        margin: 0;
    }

    .hero-tag {
        color: var(--copper-gold);
        font-weight: 700;
    }

    .hero-subtitle {
        color: var(--text-muted);
        font-size: 14px;
        margin-top: 6px;
    }

    /* Glass Cards */
    .glass-card {
        background: var(--bg-card);
        border: 1px solid var(--border-maroon);
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 20px;
        backdrop-filter: blur(16px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }

    .glass-card:hover {
        border-color: rgba(217, 119, 6, 0.6);
        transform: translateY(-2px);
    }

    /* Metric Readouts */
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .metric-label {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: var(--text-muted);
    }

    .val-green { color: var(--emerald-green); text-shadow: 0 0 10px rgba(16, 185, 129, 0.4); }
    .val-yellow { color: var(--copper-gold); text-shadow: 0 0 10px rgba(217, 119, 6, 0.4); }
    .val-red { color: #ef4444; text-shadow: 0 0 10px rgba(239, 68, 68, 0.4); }

    /* Custom Streamlit Tabs Override */
    [data-testid="stTabs"] button {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
        font-size: 15px !important;
        color: var(--text-muted) !important;
        padding: 12px 24px !important;
    }

    [data-testid="stTabs"] button[aria-selected="true"] {
        color: var(--text-bright) !important;
        border-bottom: 3px solid var(--primary-red) !important;
        background: rgba(153, 27, 27, 0.15) !important;
        border-radius: 8px 8px 0 0 !important;
    }

    /* Scrollbars */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0d0405; }
    ::-webkit-scrollbar-thumb { background: #991b1b; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #dc2626; }
</style>
""", unsafe_allow_html=True)

# ─── REAL-TIME UNCACHED DATABASE LOADERS ──────────────────────────────────────
def fetch_agents_list():
    return ["db_agent", "sec_agent", "custom"]

def fetch_agent_baseline_data(agent_id: str):
    baselines_dict = database.get_all_baselines(agent_id)
    clusters = database.get_intent_clusters(agent_id)
    overall = baselines_dict.get(-1, {}) if isinstance(baselines_dict, dict) else {}
    if not overall and baselines_dict:
        overall = list(baselines_dict.values())[0]
    return overall or {}, clusters or []

def fetch_recent_telemetry_logs(agent_id: str, limit: int = 100):
    logs = database.get_sessions(agent_id, limit=limit)
    normalized = []
    if logs:
        for log in logs:
            if isinstance(log, dict):
                normalized.append({
                    "session_id": log.get("session_id", "sess_unknown"),
                    "agent_id": log.get("agent_id", agent_id),
                    "query": log.get("query", "N/A"),
                    "cluster_id": log.get("cluster_id", 0),
                    "tool_calls": log.get("tool_calls", []),
                    "metrics": log.get("metrics", {}),
                    "anomaly_score": float(log.get("anomaly_score", 0.0)),
                    "health_tier": log.get("health_tier", "normal"),
                    "created_at": log.get("created_at", datetime.now().isoformat())
                })
    return normalized

def fetch_active_drift_alerts(agent_id: str):
    alerts = database.get_active_drift_alerts(agent_id)
    normalized = []
    if alerts:
        for a in alerts:
            if isinstance(a, dict):
                normalized.append({
                    "id": a.get("id", "N/A"),
                    "agent_id": a.get("agent_id", agent_id),
                    "message": a.get("message", "Drift alert triggered"),
                    "score": float(a.get("score", a.get("avg_score", 0.0))),
                    "status": a.get("status", "pending"),
                    "created_at": a.get("created_at", datetime.now().isoformat())
                })
    return normalized


# ─── MAIN DASHBOARD APPLICATION ───────────────────────────────────────────────
def main():
    inject_custom_theme()

    # ─── SIDEBAR CONTROL PANEL ────────────────────────────────────────────────
    st.sidebar.markdown("## 🛡️ AB³ Analytics Controls")
    st.sidebar.caption("Agent Behavioral Baseline Builder — SIEM & Telemetry Console")

    preset_labels = {
        "db_agent": "Customer DB Worker (Default)",
        "sec_agent": "Security Patching Worker",
        "custom": "Custom Blueprint"
    }

    available_agents = fetch_agents_list()
    selected_agent = st.sidebar.selectbox(
        "🎯 Target AI Agent System",
        available_agents,
        format_func=lambda x: preset_labels.get(x, f"Agent ({x})")
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎛️ Anomaly Threshold Sliders")
    tau = st.sidebar.slider("Warning Threshold (τ)", 0.10, 0.50, 0.30, 0.05,
                            help="Scores above τ mark Warning status")
    gamma = st.sidebar.slider("Severe Alert Threshold (γ)", 0.50, 0.95, 0.70, 0.05,
                             help="Scores above γ mark Severe Hijack status")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Prometheus Scrape API Status")
    st.sidebar.code("GET http://localhost:8000/metrics\nFormat: OpenMetrics / Prometheus Text", language="yaml")
    st.sidebar.info(
        "**Prometheus Telemetry Integration:**\n"
        "AB³ exposes real-time OpenMetrics counters (`agent_baseline_evaluations_total`, "
        "`agent_baseline_anomalies_total`, `agent_baseline_drift_alerts_active`) so enterprise "
        "Grafana dashboards & SIEMs can monitor agent health automatically."
    )

    # ─── FETCH AGENT DATA REAL-TIME ───────────────────────────────────────────
    overall_baseline, clusters = fetch_agent_baseline_data(selected_agent)
    telemetry_logs = fetch_recent_telemetry_logs(selected_agent, limit=100)
    drift_alerts = fetch_active_drift_alerts(selected_agent)

    # Determine Live Health Tier
    latest_score = 0.0
    current_tier = "normal"
    if telemetry_logs:
        latest_score = telemetry_logs[0]["anomaly_score"]
        if latest_score >= gamma:
            current_tier = "severe"
        elif latest_score >= tau:
            current_tier = "warning"

    # ─── TOP HERO HEADER ──────────────────────────────────────────────────────
    tier_badge_html = "<span style='color:#10b981; font-weight:800;'>🟢 NORMAL</span>"
    if current_tier == "warning":
        tier_badge_html = "<span style='color:#d97706; font-weight:800;'>🟡 WARNING</span>"
    elif current_tier == "severe":
        tier_badge_html = "<span style='color:#ef4444; font-weight:800;'>🔴 SEVERE ALARM</span>"

    st.markdown(f"""
    <div class="hero-banner">
        <div>
            <div class="hero-title">AB<sup>3</sup> Data Science &amp; Analytics Console</div>
            <div class="hero-subtitle">
                Target AI System: <span class="hero-tag">{preset_labels.get(selected_agent, selected_agent)}</span> | 
                Live Proxy Status: {tier_badge_html}
            </div>
        </div>
        <div>
            <a href="http://localhost:8000" target="_blank" style="background:#991b1b; color:#fff; padding:10px 18px; border-radius:10px; text-decoration:none; font-weight:700; font-family:'JetBrains Mono'; font-size:13px; border:1px solid #d97706;">
                🚀 Open Main AB³ App
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ─── TOP SUMMARY METRIC CARDS ─────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        color_cls = "val-green" if current_tier == "normal" else ("val-yellow" if current_tier == "warning" else "val-red")
        st.markdown(f"""
        <div class="glass-card">
            <div class="metric-value {color_cls}">{latest_score:.2f}</div>
            <div class="metric-label">Latest Anomaly Score</div>
        </div>
        """, unsafe_allow_html=True)

    with m2:
        tool_count = len(overall_baseline.get("tool_frequency", {})) if isinstance(overall_baseline, dict) else 5
        st.markdown(f"""
        <div class="glass-card">
            <div class="metric-value val-green">{tool_count}</div>
            <div class="metric-label">Monitored Tools</div>
        </div>
        """, unsafe_allow_html=True)

    with m3:
        cluster_count = len(clusters) if clusters else 3
        st.markdown(f"""
        <div class="glass-card">
            <div class="metric-value val-yellow">{cluster_count}</div>
            <div class="metric-label">Workload Baseline Clusters</div>
        </div>
        """, unsafe_allow_html=True)

    with m4:
        log_count = len(telemetry_logs)
        st.markdown(f"""
        <div class="glass-card">
            <div class="metric-value val-green">{log_count}</div>
            <div class="metric-label">Evaluated Telemetry Spans</div>
        </div>
        """, unsafe_allow_html=True)

    # ─── INTERACTIVE DETAILED TABS ────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Anomaly Seismograph & Spans",
        "🔀 Markov Transition Graph",
        "🧬 Workload Baseline Clusters",
        "🔄 Drift Alerts & Recalibration",
        "📊 Prometheus Metrics Guide"
    ])

    # ─── TAB 1: SEISMOGRAPH & SPANS FEED ──────────────────────────────────────
    with tab1:
        st.markdown("### 📈 Continuous Real-Time Anomaly Seismograph")
        st.caption("Plots live anomaly scores across execution spans. Threshold lines demarcate Normal, Warning (0.30), and Severe (0.70) threat boundaries.")

        if telemetry_logs:
            df_logs = pd.DataFrame(telemetry_logs)
            df_logs["created_at_dt"] = pd.to_datetime(df_logs["created_at"])
            df_logs = df_logs.sort_values(by="created_at_dt", ascending=True)

            fig = px.line(
                df_logs,
                x="created_at_dt",
                y="anomaly_score",
                hover_data=["session_id", "query", "health_tier"],
                title=f"Telemetry Anomaly Stream for {selected_agent}",
                markers=True
            )
            fig.update_traces(line_color="#991B1B", line_width=3, marker=dict(size=9, color="#D97706"))
            fig.add_hline(y=tau, line_dash="dash", line_color="#D97706", annotation_text=f"Warning Threshold (τ = {tau:.2f})")
            fig.add_hline(y=gamma, line_dash="dash", line_color="#EF4444", annotation_text=f"Severe Alert Threshold (γ = {gamma:.2f})")
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20,7,9,0.7)",
                font=dict(color="#ffffff", family="Outfit"),
                yaxis=dict(range=[0, 1.05], gridcolor="rgba(153,27,27,0.2)"),
                xaxis=dict(gridcolor="rgba(153,27,27,0.2)")
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("### 📋 Live Execution Span Table")
            filter_tier = st.multiselect("Filter by Health Tier", ["NORMAL", "WARNING", "ALERT", "SEVERE"], default=["NORMAL", "WARNING", "ALERT", "SEVERE"])
            
            df_display = df_logs.copy()
            df_display["health_tier_upper"] = df_display["health_tier"].str.upper()
            filtered_df = df_display[df_display["health_tier_upper"].isin(filter_tier)].sort_values(by="created_at_dt", ascending=False)
            
            st.dataframe(
                filtered_df[["session_id", "created_at", "health_tier_upper", "anomaly_score", "cluster_id", "query"]],
                column_config={
                    "session_id": "Session ID",
                    "created_at": "Timestamp",
                    "health_tier_upper": "Health Tier",
                    "anomaly_score": st.column_config.NumberColumn("Anomaly Score", format="%.2f"),
                    "cluster_id": "Cluster #",
                    "query": "Incoming User Query"
                },
                use_container_width=True
            )
        else:
            st.warning("No telemetry spans recorded yet for this agent. Use the Main AB³ UI to simulate traffic.")

    # ─── TAB 2: MARKOV TRANSITIONS MATRIX ─────────────────────────────────────
    with tab2:
        st.markdown("### 🔀 Directed Markov Tool Call Transition Probability Matrix")
        st.caption("Visualizes calculated transition probabilities P(T_next | T_current). Transitions with P=0.0 between unregistered tools force a 1.00 Hijack Penalty.")

        markov_trans = overall_baseline.get("markov_transitions", {}) if isinstance(overall_baseline, dict) else {}
        if markov_trans:
            all_tools = sorted(list(set(list(markov_trans.keys()) + [t for sub in markov_trans.values() for t in sub.keys()])))
            
            matrix_data = []
            for src in all_tools:
                row = []
                for tgt in all_tools:
                    prob = markov_trans.get(src, {}).get(tgt, 0.0)
                    row.append(prob)
                matrix_data.append(row)

            fig_hm = px.imshow(
                matrix_data,
                x=all_tools,
                y=all_tools,
                color_continuous_scale="Reds",
                text_auto=".2f",
                title="Transition Matrix P(T_next | T_current)"
            )
            fig_hm.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20,7,9,0.7)",
                font=dict(color="#ffffff", family="Outfit")
            )
            st.plotly_chart(fig_hm, use_container_width=True)
        else:
            st.info("No Markov transition matrix available for this agent yet. Profile the agent baseline in Module 1.")

    # ─── TAB 3: WORKLOAD BASELINE CLUSTERS ────────────────────────────────────
    with tab3:
        st.markdown("### 🧬 Workload Baseline Clusters (K-Means)")
        st.caption("Synthesized scenarios grouped by task category using TF-IDF and K-Means clustering. Incoming production queries are routed to their nearest cluster for precise scoring.")

        if clusters:
            cols = st.columns(len(clusters))
            for idx, c in enumerate(clusters):
                cid = c.get("cluster_id", idx)
                cdata = c.get("data", {})
                with cols[idx]:
                    st.markdown(f"""
                    <div class="glass-card">
                        <h4 style="color:#d97706; margin-top:0;">Workload Cluster #{cid + 1}</h4>
                        <p><strong>Category:</strong> {cdata.get('intent', cdata.get('category', 'Data Operations'))}</p>
                        <p><strong>Sample Query:</strong> <em>"{cdata.get('sample_query', 'N/A')}"</em></p>
                        <p><strong>Primary Tools:</strong> <code>{', '.join(cdata.get('primary_tools', ['read_user']))}</code></p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("Synthesize baseline scenarios in Module 1 to view K-Means workload clusters.")

    # ─── TAB 4: DRIFT ALERTS ──────────────────────────────────────────────────
    with tab4:
        st.markdown("### 🔄 Baseline Drift Detector & Auto-Refresh Engine")
        st.caption("Tracks long-term sliding window anomaly metrics over time. Alerts trigger when sustained drift is detected across production spans.")

        if drift_alerts:
            df_drift = pd.DataFrame(drift_alerts)
            st.dataframe(
                df_drift[["id", "created_at", "message", "score", "status"]],
                column_config={
                    "id": "Alert ID",
                    "created_at": "Triggered At",
                    "message": "Drift Alert Message",
                    "score": st.column_config.NumberColumn("Avg Anomaly Score", format="%.2f"),
                    "status": "Alert Status"
                },
                use_container_width=True
            )
        else:
            st.success("✔ Baseline Status: STABLE. No active drift alerts recorded.")

    # ─── TAB 5: PROMETHEUS METRICS GUIDE ──────────────────────────────────────
    with tab5:
        st.markdown("### 📊 Prometheus & OpenMetrics Enterprise Guide")
        st.write("""
        ### What are Prometheus Metrics?
        **Prometheus** is the industry-standard monitoring and alerting platform for cloud-native software. 
        Instead of pushing logs manually, Prometheus regularly scrapes a standardized endpoint (`/metrics`) to collect time-series metrics.

        ### AB³ Exposed Prometheus Metrics
        The AB³ proxy engine exposes OpenMetrics data at `http://localhost:8000/metrics`:

        1. `agent_baseline_active_agents` *(Gauge)*: Total number of AI agents currently profiled in the database.
        2. `agent_baseline_evaluations_total` *(Counter)*: Cumulative count of live execution spans evaluated by the proxy.
        3. `agent_baseline_anomalies_total` *(Counter)*: Cumulative count of severe anomalous execution spans detected.
        4. `agent_baseline_drift_alerts_active` *(Gauge)*: Active baseline drift alerts pending resolution.

        ### How Enterprise Security Teams Use This:
        * **Grafana Dashboards:** Plug `http://localhost:8000/metrics` into Grafana for SOC monitoring.
        * **PagerDuty / Slack Alerts:** Automatically wake up security operators if `agent_baseline_anomalies_total` spikes unexpectedly.
        """)

if __name__ == "__main__":
    main()
