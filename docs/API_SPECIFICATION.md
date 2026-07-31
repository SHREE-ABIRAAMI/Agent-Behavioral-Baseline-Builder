# REST API Specification

> **Project:** Agent Behavioral Baseline Builder (AB³)  
> **Author & Lead Architect:** SHREE ABIRAAMI M  

---

## 📌 Endpoint Overview

| Path | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Main Web Application UI Dashboard |
| `/healthz` | `GET` | Health Check Endpoint |
| `/metrics` | `GET` | Prometheus / OpenMetrics Telemetry Endpoint |
| `/api/agents/profile` | `POST` | Execute Module 1 & Module 2 Baseline Profiling (50 Scenarios) |
| `/api/agents/{agent_id}/baseline` | `GET` | Fetch Active Behavioral Baseline Fingerprint |
| `/api/monitor` | `POST` | Ingest & Evaluate Real-Time Telemetry Span |
| `/api/drift/alerts` | `GET` | Fetch Active & Historical Drift Alerts |
| `/api/drift/refresh` | `POST` | Execute 1-Click Baseline Recalibration |

---

## 📥 Sample Request & Response Schemas

### `POST /api/monitor` — Ingest Production Telemetry Span

#### Request Payload:
```json
{
  "agent_id": "db_agent",
  "query": "Fetch customer account details for user ID USR-4910.",
  "tool_calls": ["read_user", "audit_log"],
  "parameter_lengths": [25, 40],
  "response_length": 150
}
```

#### Response Payload:
```json
{
  "session_id": "sess_a81f0b",
  "agent_id": "db_agent",
  "cluster_id": 0,
  "anomaly_score": 0.08,
  "health_tier": "normal",
  "metrics": {
    "tool_frequency_distance": 0.04,
    "markov_anomaly_score": 0.0,
    "bounds_anomaly_score": 0.08
  }
}
```

---

### `GET /metrics` — Prometheus OpenMetrics Endpoint

#### Response Format (`text/plain`):
```text
# HELP agent_baseline_active_agents Total profiled agents
# TYPE agent_baseline_active_agents gauge
agent_baseline_active_agents 3
# HELP agent_baseline_evaluations_total Total telemetry spans evaluated
# TYPE agent_baseline_evaluations_total counter
agent_baseline_evaluations_total 128
# HELP agent_baseline_anomalies_total Total severe anomalous executions detected
# TYPE agent_baseline_anomalies_total counter
agent_baseline_anomalies_total 4
# HELP agent_baseline_drift_alerts_active Active drift alerts pending resolution
# TYPE agent_baseline_drift_alerts_active gauge
agent_baseline_drift_alerts_active 0
```
