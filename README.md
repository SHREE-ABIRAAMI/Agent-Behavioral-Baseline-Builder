# AB³ — Agent Behavioral Baseline Builder

> **Automated pre-deployment profiling and real-time behavioral drift monitoring platform for enterprise AI agents.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python)](https://www.python.org)
[![Prometheus](https://img.shields.io/badge/Prometheus-OpenMetrics-E6522C.svg?style=flat&logo=prometheus)](https://prometheus.io)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-10b981.svg?style=flat)](#)

---

## 🎯 Problem Statement Overview

Enterprise AI agents face a critical **"cold-start governance problem"**: newly deployed models operate ungoverned for weeks because security teams lack historical operational data to define what "normal" behavior looks like.

**AB³ (Agent Behavioral Baseline Builder)** solves this by executing an automated pre-deployment profiling pipeline before an agent processes its first real user request. Inspecting the agent's system prompt and tool definitions, AB³ synthesizes **50 diverse test scenarios**, executes them in an isolated sandbox, and constructs a high-dimensional **Behavioral Fingerprint** (tool invocation frequency matrices, response length distributions, tool call transition graphs, and data access scope). 

In production, an OpenTelemetry-compatible proxy continuously evaluates live execution spans against this baseline, flagging statistical anomalies and triggering automated governance actions when long-term behavioral drift is detected.

---

## 🏗️ System Architecture

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

## ✨ Key Features & Pipeline Modules

### 🧬 Module 1: Pre-Deployment Scenario Synthesizer
* **50 Synthetic Scenarios**: Automatically generates 50 diverse test scenarios covering normal operational paths, edge cases, and unexpected query variants.
* **LLM & Procedural Engines**: Uses Anthropic Claude, OpenAI, or a robust procedural fallback generator when external APIs are unavailable.

### 📊 Module 2: Workload Baseline Profiler & Fingerprinting
* **Behavioral Fingerprint**: Extracts tool invocation frequencies, parameter length distributions, and Markov transition matrices.
* **K-Means Intent Clustering**: Uses TF-IDF vectorization and K-Means clustering to group scenarios by task intent so incoming queries are scored against their nearest intent sub-baseline.

### 🛡️ Module 3: Production Real-Time Proxy & Telemetry Engine
* **Directed Markov Graph Check**: Computes transition probabilities $P(T_{\text{next}} \mid T_{\text{current}})$. Unregistered tool calls immediately trigger a $1.00$ Hijack Penalty.
* **Continuous Health Tiers**: Evaluates incoming spans into three real-time tiers:
  * 🟢 **Normal** ($\text{Score} < 0.30$)
  * 🟡 **Warning** ($0.30 \le \text{Anomaly Score} < 0.70$)
  * 🔴 **Severe Alarm / Hijack** ($\text{Anomaly Score} \ge 0.70$)
* **Live Anomaly Seismograph**: Real-time visualization plotting anomaly score streams over time.

### 🔄 Module 4: Baseline Drift Detector & Auto-Refresh Engine
* **Sliding-Window Aggregation**: Monitors long-term divergence across production spans.
* **1-Click Baseline Recalibration**: Allows 1-click baseline updates to align with intentional model or prompt updates.

---

## 📂 Project Directory Structure

```text
agent-baseline-builder/
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI Workflow
├── app/
│   ├── scenario_generator/    # Module 1: 50 Scenario Synthesizer
│   ├── profiler/              # Module 2: Sandbox Profiler & Fingerprint Generator
│   ├── monitor_proxy/         # Module 3: Real-Time Proxy & Markov Evaluation Engine
│   ├── drift_detector/        # Module 4: Sliding Window Drift & Auto-Refresh Engine
│   ├── models/                # SQLAlchemy & DB Schema Definitions
│   ├── storage/               # Abstract Postgres / SQLite Repositories
│   ├── static/                # Dark Glassmorphism Frontend (HTML, CSS, JS)
│   └── main.py                # FastAPI Application Entrypoint & /metrics Endpoint
├── docs/
│   ├── ARCHITECTURE.md        # Deep Architectural Specifications
│   └── API_SPECIFICATION.md   # Comprehensive REST API Reference
├── tests/                     # Pytest & Unittest Test Suites
├── deploy/                    # Deployment Templates (AWS / Docker)
├── simulation/                # Live Telemetry Traffic Simulator
├── .gitignore                 # Tracked Files Exclusion Rules
├── docker-compose.yml         # Docker Services Orchestration
├── Dockerfile                 # Container Blueprint
├── LICENSE                    # MIT License (SHREE ABIRAAMI M)
├── README.md                  # Main Documentation Entrypoint
├── requirements.txt           # Dependencies Manifest
└── run.py                     # Application Launcher
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites & Virtual Environment Setup

```bash
# Clone the repository
git clone https://github.com/SHREE-ABIRAAMI/Agent-Behavioral-Baseline-Builder.git
cd Agent-Behavioral-Baseline-Builder

# Create python virtual environment
python -m venv venv

# Activate environment (Windows)
venv\Scripts\activate

# Activate environment (Linux/macOS)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### 2. Launching the Application

Start the FastAPI application proxy:

```bash
python run.py
```

The web dashboard will be available at:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## 🔌 API Reference Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Main Web Application UI Dashboard |
| `/healthz` | `GET` | Health Check Endpoint (`HTTP 200 OK`) |
| `/metrics` | `GET` | Prometheus / OpenMetrics Telemetry Endpoint |
| `/api/agents/profile` | `POST` | Execute Module 1 & Module 2 Baseline Profiling (50 Scenarios) |
| `/api/agents/{agent_id}/baseline` | `GET` | Retrieve Active Agent Behavioral Baseline Fingerprint |
| `/api/monitor` | `POST` | Ingest & Evaluate Real-Time Telemetry Span |
| `/api/drift/alerts` | `GET` | Fetch Active & Historical Drift Alerts |
| `/api/drift/refresh` | `POST` | Execute 1-Click Baseline Recalibration |

Detailed request & response JSON schemas are documented in [`docs/API_SPECIFICATION.md`](docs/API_SPECIFICATION.md).

---

## 📊 Prometheus OpenMetrics Integration

Enterprise security teams can scrape metrics directly from `http://localhost:8000/metrics`.

Exposed metrics include:
* `agent_baseline_active_agents` *(Gauge)*: Total number of profiled agents.
* `agent_baseline_evaluations_total` *(Counter)*: Cumulative count of evaluated telemetry spans.
* `agent_baseline_anomalies_total` *(Counter)*: Cumulative count of severe anomalous execution spans detected.
* `agent_baseline_drift_alerts_active` *(Gauge)*: Count of active baseline drift alerts pending resolution.

---

## 🐳 Docker Container Deployment

To launch the full stack using Docker:

```bash
docker-compose up --build
```

---

## 📜 License & Compliance

Developed for enterprise AI governance and security monitoring. Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.

---

## 👩‍💻 Author & Lead Architect

**SHREE ABIRAAMI M**  
*Creator & Developer — Agent Behavioral Baseline Builder (AB³)*  
🔗 [GitHub Profile](https://github.com/SHREE-ABIRAAMI)
