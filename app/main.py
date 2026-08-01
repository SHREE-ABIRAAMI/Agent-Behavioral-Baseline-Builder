import json
import uuid
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
import structlog

import app.database as database
import app.config as config
from app.scenario_generator import generate_scenarios, cluster_scenarios, save_clustering_models
from app.profiler import SandboxProfiler
from app.monitor_proxy import TelemetryMonitor
from app.drift_detector import DriftDetector, trigger_baseline_refresh

# Configure structlog JSON logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger("agent_baseline.main")

app = FastAPI(
    title="AEGIS: Agent Execution Genome & Intent Sentinel API",
    description="Cold-Start AI Governance & Behavioral Genome Profiling Platform for Enterprise AI Agents.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket Manager for broadcasting telemetry spans to UI
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# Pydantic Schemas
class ToolSpec(BaseModel):
    name: str
    description: str

class AgentProfileRequest(BaseModel):
    agent_id: str
    name: str
    description: Optional[str] = ""
    system_prompt: str
    tools: List[ToolSpec]

class MonitorRequest(BaseModel):
    agent_id: str
    query: str
    tool_calls: List[str]
    parameter_lengths: List[int]
    response_length: int

@app.on_event("startup")
def startup_event():
    logger.info("Initializing baseline database schemas via SQLAlchemy...")
    database.init_db()

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "Agent Behavioral Baseline Builder"}

@app.get("/metrics")
def metrics(request: Request):
    # Read live counts from the database
    db_agents = database.list_agents()
    agent_ids = set(["db_agent", "sec_agent"])
    for a in db_agents:
        aid = a.get("id") if isinstance(a, dict) else getattr(a, "id", None)
        if aid:
            agent_ids.add(aid)

    total_agents = len(agent_ids)
    total_sessions = 0
    total_anomalies = 0
    total_alerts = 0

    for aid in agent_ids:
        sessions = database.get_sessions(aid, limit=10000)
        total_sessions += len(sessions)
        total_anomalies += sum(1 for s in sessions if s.get("anomaly_score", 0.0) >= 0.70)
        alerts = database.get_active_drift_alerts(aid)
        total_alerts += len(alerts)

    prometheus_data = f"""# HELP agent_baseline_active_agents Total profiled agents
# TYPE agent_baseline_active_agents gauge
agent_baseline_active_agents {total_agents}
# HELP agent_baseline_evaluations_total Total telemetry spans evaluated
# TYPE agent_baseline_evaluations_total counter
agent_baseline_evaluations_total {total_sessions}
# HELP agent_baseline_anomalies_total Total severe anomalous executions detected
# TYPE agent_baseline_anomalies_total counter
agent_baseline_anomalies_total {total_anomalies}
# HELP agent_baseline_drift_alerts_active Active drift alerts pending resolution
# TYPE agent_baseline_drift_alerts_active gauge
agent_baseline_drift_alerts_active {total_alerts}
"""
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prometheus Metrics - AB³ Baseline Builder</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&family=Fira+Code:wght@500;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons+Round" rel="stylesheet">
    <style>
        body {{ background: #0c0406; color: #ffffff; font-family: 'Outfit', sans-serif; padding: 30px; margin: 0; }}
        .header-bar {{ display: flex; justify-content: space-between; align-items: center; background: rgba(30, 10, 15, 0.9); padding: 16px 24px; border-radius: 12px; border: 1px solid rgba(153, 27, 27, 0.4); margin-bottom: 24px; }}
        .btn-back {{ display: inline-flex; align-items: center; gap: 8px; background: #991b1b; color: #ffffff; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 14px; transition: all 0.2s ease; cursor: pointer; }}
        .btn-back:hover {{ background: #b91c1c; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(153, 27, 27, 0.5); }}
        pre {{ background: #140709; padding: 24px; border-radius: 12px; border: 1px solid rgba(153, 27, 27, 0.3); font-family: 'Fira Code', monospace; color: #f59e0b; font-size: 14px; line-height: 1.6; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="header-bar">
        <h2 style="margin:0; display:flex; align-items:center; gap:10px;"><span class="material-icons-round" style="color:#ef4444;">query_stats</span> Prometheus Live Metrics Endpoint</h2>
        <a href="/" class="btn-back"><span class="material-icons-round">arrow_back</span> ← Back to Dashboard</a>
    </div>
    <pre>{prometheus_data}</pre>
</body>
</html>"""
        return HTMLResponse(content=html_content)

    return Response(content=prometheus_data, media_type="text/plain")

@app.get("/api/presets")
def get_presets():
    return {
        "db_agent": {
            "name": "Customer DB & Operations Agent",
            "description": "Agent managing customer database records, account statuses, and audit logs.",
            "system_prompt": "You are a customer database management agent. You assist authorized staff by fetching user records, updating account statuses, and purging temporary data. Always log audit trails.",
            "tools": [
                {"name": "read_user", "description": "Read customer details from database"},
                {"name": "update_user_status", "description": "Update user account status (e.g. active, suspended)"},
                {"name": "delete_user", "description": "Purge customer user record from database"},
                {"name": "send_email", "description": "Dispatch notification email to customer"},
                {"name": "log_audit", "description": "Write operational audit log"}
            ]
        },
        "sec_agent": {
            "name": "Security Vulnerability Patching Agent",
            "description": "Agent scanning vulnerability reports and applying hotfixes.",
            "system_prompt": "You are a security patching agent. You analyze CVE reports, fetch source code, apply hotfixes, and deploy patches.",
            "tools": [
                {"name": "fetch_cve", "description": "Fetch CVE security vulnerability details"},
                {"name": "read_code", "description": "Inspect repository source code"},
                {"name": "apply_patch", "description": "Apply security hotfix patch"},
                {"name": "run_tests", "description": "Run automated verification tests"},
                {"name": "deploy_service", "description": "Deploy patched service container"}
            ]
        }
    }

@app.post("/api/agents/profile")
def profile_agent(req: AgentProfileRequest):
    tools_list = [t.dict() for t in req.tools]
    database.save_agent(req.agent_id, req.name, req.description, req.system_prompt, tools_list)

    scenarios = generate_scenarios(req.agent_id, req.system_prompt, tools_list)
    clustering = cluster_scenarios(scenarios, num_clusters=3)
    save_clustering_models(req.agent_id, clustering["vectorizer"], clustering["kmeans"])

    profiler = SandboxProfiler(req.agent_id)
    baselines = profiler.profile_scenarios(scenarios, clustering["labels"], num_clusters=3)
    database.save_intent_clusters(req.agent_id, clustering["clusters"])

    return {
        "status": "success",
        "agent_id": req.agent_id,
        "scenarios_count": len(scenarios),
        "clusters": clustering["clusters"],
        "scenarios": scenarios,
        "overall_fingerprint": baselines.get(-1, {})
    }

@app.get("/api/agents/{agent_id}")
def get_agent_profile(agent_id: str):
    agent = database.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent profile not found")

    baselines_dict = database.get_all_baselines(agent_id)
    clusters = database.get_intent_clusters(agent_id)
    alerts = database.get_active_drift_alerts(agent_id)

    return {
        "agent": agent,
        "clusters": clusters,
        "active_drift_alerts": alerts,
        "baselines": [
            {"cluster_id": c_id, "fingerprint": fp}
            for c_id, fp in baselines_dict.items()
        ]
    }

@app.get("/api/agents/{agent_id}/baseline")
def get_agent_baseline_endpoint(agent_id: str):
    agent = database.get_agent(agent_id)
    baselines_dict = database.get_all_baselines(agent_id)
    clusters = database.get_intent_clusters(agent_id)
    
    # Generate representative scenarios from cluster baselines (exactly 50 scenarios)
    scenarios = []
    if clusters:
        num_clusters = len(clusters)
        base_per_cluster = 50 // num_clusters
        remainder = 50 % num_clusters
        for idx, c in enumerate(clusters):
            count = base_per_cluster + (1 if idx < remainder else 0)
            sample_q = c.get("sample_query") or "Fetch database record"
            tools = c.get("primary_tools") or ["read_user", "audit_log"]
            for i in range(count):
                scenarios.append({
                    "scenario_id": f"scen_{len(scenarios)+1}",
                    "category": c.get("category", "Data Retrieval"),
                    "query": f"{sample_q} (Variant #{i+1})",
                    "tools": tools,
                    "expected_tools": tools
                })
    else:
        # Default fallback scenarios (50 scenarios)
        for i in range(1, 51):
            scenarios.append({
                "scenario_id": f"scen_{i}",
                "category": "Data Operations" if i <= 25 else ("Boundary Checks" if i <= 35 else "Audit Logging"),
                "query": f"Fetch customer account details for user ID USR-{4000+i}.",
                "tools": ["read_user", "audit_log"],
                "expected_tools": ["read_user", "audit_log"]
            })

    return {
        "status": "success",
        "agent": agent,
        "overall": baselines_dict.get(-1, {}) or baselines_dict.get(0, {}),
        "clusters": clusters,
        "scenarios": scenarios
    }

@app.get("/api/drift/alerts")
def get_drift_alerts(agent_id: str):
    alerts = database.get_active_drift_alerts(agent_id)
    return {"status": "success", "active_alerts": alerts}

@app.post("/api/agents/{agent_id}/refresh")
def refresh_agent_baseline(agent_id: str):
    res = trigger_baseline_refresh(agent_id)
    return res

@app.post("/api/drift/refresh")
def refresh_drift_endpoint(agent_id: str):
    res = trigger_baseline_refresh(agent_id)
    return res

@app.post("/api/monitor")
async def monitor_span(req: MonitorRequest):
    agent = database.get_agent(req.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{req.agent_id}' not profiled")

    monitor = TelemetryMonitor(req.agent_id)
    res = monitor.evaluate_execution(
        query=req.query,
        tool_calls=req.tool_calls,
        param_lengths=req.parameter_lengths,
        response_length=req.response_length
    )

    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    database.save_session(
        session_id=session_id,
        agent_id=req.agent_id,
        query=req.query,
        cluster_id=res["cluster_id"],
        tool_calls=req.tool_calls,
        metrics=res["metrics"],
        anomaly_score=res["anomaly_score"],
        health_tier=res["health_tier"]
    )

    session_payload = {
        "id": session_id,
        "agent_id": req.agent_id,
        "query": req.query,
        "cluster_id": res["cluster_id"],
        "tool_calls": req.tool_calls,
        "metrics": res["metrics"],
        "anomaly_score": res["anomaly_score"],
        "health_tier": res["health_tier"],
        "created_at": database.get_sessions(req.agent_id, limit=1)[0]["created_at"] if database.get_sessions(req.agent_id, limit=1) else ""
    }

    database.redis_cache_session(req.agent_id, session_payload)

    detector = DriftDetector(req.agent_id)
    drift_status = detector.evaluate_recent_window()

    await manager.broadcast({
        "event": "new_session",
        "session": session_payload,
        "drift": drift_status
    })

    return session_payload

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Static files for HTML client
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    handler = None
