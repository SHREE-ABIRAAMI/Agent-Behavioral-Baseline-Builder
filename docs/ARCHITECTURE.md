# System Architecture & Technical Specifications

> **Project:** Agent Behavioral Baseline Builder (AB³)  
> **Author & Lead Architect:** SHREE ABIRAAMI M  

---

## 🏗️ Architectural Overview

AB³ is a pre-deployment profiling and production telemetry monitoring platform designed to solve the **AI Agent Cold-Start Governance Problem**.

```text
+-----------------------------------------------------------------------------------+
|                            ENTERPRISE AI AGENT PIPELINE                           |
+-----------------------------------------------------------------------------------+
                                          |
                        Ingest Spans (OpenTelemetry JSON)
                                          v
+-----------------------------------------------------------------------------------+
|               MODULE 3: PRODUCTION REAL-TIME MONITORING PROXY (FastAPI)           |
|                                                                                   |
|  +---------------------------+  +---------------------------+  +----------------+ |
|  | Intent Cluster Predictor  |  | Directed Markov Checker   |  | Statistical    | |
|  | (K-Means & TF-IDF Match)  |  | (P=0.0 Hijack Alarm)      |  | Distance SciPy | |
|  +---------------------------+  +---------------------------+  +----------------+ |
+-----------------------------------------------------------------------------------+
         |                                |                               |
         | Fetch Fingerprint              | Read/Write Stats              | Health Tier
         v                                v                               v
+------------------+             +------------------+            +------------------+
| MODULE 2:        |             | DB STORAGE /     |            | 3 HEALTH TIERS:  |
| SANDBOX PROFILER |             | REPOSITORY       |            | <0.30 Normal     |
| (SQLAlchemy /    |             | (SQLite / PG)    |            | 0.30-0.70 Warning|
| Postgres DB)     |             +------------------+            | >=0.70 Alert     |
+------------------+                                             +------------------+
         ^                                                                |
         | Synthesize 50 Scenarios                                        v
+------------------+                                             +------------------+
| MODULE 1:        | <------------- 1-Click Baseline Recalibration- | MODULE 4:        |
| SYNTHETIC SCENARIO|                                            | DRIFT DETECTOR   |
| GENERATOR        |                                             | ENGINE           |
+------------------+                                             +------------------+
```

---

## 🧩 Core Pipeline Components

### 1. Module 1 — Synthetic Scenario Generator (`app/scenario_generator`)
- **Objective:** Generate 50 synthetic test scenarios covering expected behavior, edge cases, and unexpected query variants before an agent processes real user traffic.
- **Engines Supported:** Anthropic Claude (`claude-3-haiku`), OpenAI (`gpt-4o-mini`), and Procedural Fallback Engine.

### 2. Module 2 — Workload Baseline Profiler (`app/profiler`)
- **Behavioral Fingerprint Extraction:**
  - **Tool Frequency Distribution:** $\text{P}(\text{Tool}_i)$ probability matrix.
  - **Response & Parameter Length Z-Scores:** Mean $\mu$ and standard deviation $\sigma$.
  - **Directed Markov Graph:** Tool call transition probabilities $\text{P}(\text{Tool}_{\text{next}} \mid \text{Tool}_{\text{current}})$.
- **Intent Clustering (Bonus):** TF-IDF vectorization and K-Means clustering ($K=3$) group scenarios into Intent Clusters ($C_0, C_1, C_2$) with dedicated sub-baselines.

### 3. Module 3 — Production Monitoring Proxy (`app/monitor_proxy`)
- **Real-Time Evaluation:** Evaluates OpenTelemetry JSON spans against active baselines.
- **Continuous Threat Scoring:**
  - 🟢 **Normal:** $\text{Anomaly Score} < 0.30$
  - 🟡 **Warning:** $0.30 \le \text{Anomaly Score} < 0.70$
  - 🔴 **Severe Alarm / Hijack:** $\text{Anomaly Score} \ge 0.70$

### 4. Module 4 — Baseline Drift Detector (`app/drift_detector`)
- **Sliding-Window Aggregation:** Calculates sliding window averages across recent production runs.
- **Recalibration Engine:** Emits `Baseline Drift Alert` on sustained divergence and provides a 1-Click Baseline Recalibration trigger.
