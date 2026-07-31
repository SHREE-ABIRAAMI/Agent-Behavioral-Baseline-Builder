import os
import sys
import json
import gradio as gr

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import app.config as config
import app.database as database
from app.scenario_generator import generate_scenarios, cluster_scenarios, save_clustering_models
from app.profiler import SandboxProfiler
from app.monitor_proxy import TelemetryMonitor
from app.drift_detector import DriftDetector, trigger_baseline_refresh

# Initialize DB
database.init_db()

def profile_agent_fn(agent_id, name, system_prompt, tools_json_str):
    try:
        tools = json.loads(tools_json_str)
    except Exception as e:
        return f"Invalid Tools JSON: {e}", "", ""
        
    database.save_agent(agent_id, name, "Gradio Agent", system_prompt, tools)
    scenarios = generate_scenarios(agent_id, system_prompt, tools)
    clustering = cluster_scenarios(scenarios, num_clusters=3)
    save_clustering_models(agent_id, clustering["vectorizer"], clustering["kmeans"])

    profiler = SandboxProfiler(agent_id)
    baselines = profiler.profile_scenarios(scenarios, clustering["labels"], num_clusters=3)
    database.save_intent_clusters(agent_id, clustering["clusters"])

    overall_fp = baselines.get(-1, {})
    return (
        f"✔ Baseline Synthesis Complete! 50 scenarios generated.",
        json.dumps(clustering["clusters"], indent=2),
        json.dumps(overall_fp, indent=2)
    )

def evaluate_span_fn(agent_id, query, tool_calls_str, param_lens_str, response_len):
    try:
        tool_calls = [t.strip() for t in tool_calls_str.split(",") if t.strip()] or ["read_user", "audit_log"]
        param_lengths = [int(x.strip()) for x in param_lens_str.split(",") if x.strip()] or [25, 45]
        response_length = int(response_len)
    except Exception as e:
        return f"Error parsing inputs: {e}", "", ""

    monitor = TelemetryMonitor(agent_id)
    res = monitor.evaluate_execution(
        query=query,
        tool_calls=tool_calls,
        param_lengths=param_lengths,
        response_length=response_length
    )

    score = res.get("anomaly_score", 0.0)
    tier = res.get("health_tier", "normal").upper()
    badge = f"🟢 {tier}" if tier == "NORMAL" else ("🟡 " + tier if tier == "WARNING" else "🔴 " + tier)
    
    database.save_session(
        session_id=res.get("session_id", "sess_1"),
        agent_id=agent_id,
        query=query,
        cluster_id=res.get("cluster_id", 0),
        tool_calls=tool_calls,
        metrics=res.get("metrics", {}),
        anomaly_score=score,
        health_tier=res.get("health_tier", "normal")
    )

    return (
        f"Health Tier: {badge} | Anomaly Score: {score:.2f}",
        json.dumps(res.get("unexpected_transitions", []), indent=2),
        json.dumps(res, indent=2)
    )

def trigger_recalibration_fn(agent_id):
    trigger_baseline_refresh(agent_id)
    return f"✔ 1-Click Baseline Recalibration completed for agent '{agent_id}'!"

with gr.Blocks(title="AB³ — Agent Behavioral Baseline Builder") as demo:
    gr.Markdown("""
    # 🛡️ AB³ — Agent Behavioral Baseline Builder
    ### Automated Pre-Deployment Profiling & Real-Time Behavioral Drift Monitoring Platform for Enterprise AI Agents
    Developed by **SHREE ABIRAAMI M** | Enterprise AI Governance & Security Stack
    """)

    with gr.Tabs():
        with gr.TabItem("🧬 1. Behavioral Profiler"):
            gr.Markdown("### Pre-Deployment Synthetic Scenario Synthesis (50 Scenarios)")
            with gr.Row():
                agent_id_in = gr.Textbox(label="Agent ID", value="db_agent", interactive=True)
                name_in = gr.Textbox(label="Agent Name", value="Customer DB Worker (Default)", interactive=True)
            system_prompt_in = gr.Textbox(
                label="System Prompt", 
                value="You are a helpful customer support and database assistant. Read user profiles and send alert emails.", 
                lines=3
            )
            tools_json_in = gr.Textbox(
                label="Tool Definitions (JSON)", 
                value=json.dumps([
                    {"name": "read_user", "description": "Fetch user details"},
                    {"name": "update_status", "description": "Update user status"},
                    {"name": "send_email", "description": "Send email alert"},
                    {"name": "audit_log", "description": "Audit logging"}
                ], indent=2), 
                lines=8
            )
            
            btn_profile = gr.Button("⚡ Synthesize Behavioral Baseline (50 Scenarios)", variant="primary")
            
            status_out = gr.Textbox(label="Status")
            clusters_out = gr.Code(label="Intent Clusters (K-Means K=3)", language="json")
            fp_out = gr.Code(label="Overall Fingerprint (Markov & Z-Scores)", language="json")

            btn_profile.click(
                profile_agent_fn, 
                inputs=[agent_id_in, name_in, system_prompt_in, tools_json_in], 
                outputs=[status_out, clusters_out, fp_out]
            )

        with gr.TabItem("🛡️ 2. Real-Time Telemetry Monitor Proxy"):
            gr.Markdown("### Live OpenTelemetry Span Evaluation & Threat Scoring")
            mon_agent_id = gr.Textbox(label="Target Agent ID", value="db_agent")
            query_in = gr.Textbox(label="Incoming User Query", value="Fetch account details for user Johndoe.")
            tool_calls_in = gr.Textbox(label="Executed Tool Calls (comma-separated)", value="read_user, audit_log")
            param_lens_in = gr.Textbox(label="Parameter Lengths (comma-separated)", value="25, 45")
            resp_len_in = gr.Number(label="Response Length", value=150)

            btn_eval = gr.Button("🔍 Intercept & Evaluate Telemetry Span", variant="primary")

            mon_status_out = gr.Textbox(label="Telemetry Proxy Health Status")
            unexpected_out = gr.Code(label="Unexpected Tool Transitions (Hijack Alarms)", language="json")
            full_res_out = gr.Code(label="Full Evaluation JSON", language="json")

            btn_eval.click(
                evaluate_span_fn, 
                inputs=[mon_agent_id, query_in, tool_calls_in, param_lens_in, resp_len_in], 
                outputs=[mon_status_out, unexpected_out, full_res_out]
            )

        with gr.TabItem("🔄 3. Drift Detector & Recalibration"):
            gr.Markdown("### Rolling Window Drift Tracking & 1-Click Baseline Refresh")
            drift_agent_id = gr.Textbox(label="Agent ID", value="db_agent")
            btn_recal = gr.Button("🔄 Execute 1-Click Baseline Recalibration", variant="secondary")
            drift_status_out = gr.Textbox(label="Recalibration Status")

            btn_recal.click(
                trigger_recalibration_fn, 
                inputs=[drift_agent_id], 
                outputs=[drift_status_out]
            )

if __name__ == "__main__":
    demo.launch()
