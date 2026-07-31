# Architecture & Engineering Decisions (DECISIONS.md)

This document records key technical decisions, trade-offs, and architectural design choices for **Agent Behavioral Baseline Builder**.

---

## 1. Storage Abstraction & Dual Driver Strategy
* **Decision:** Implement abstract repository interfaces (`BaseAgentRepository`, `BaseBaselineRepository`, `BaseSessionRepository`) in `app/storage/base.py` backed by SQLAlchemy (`postgres_repo.py`) and Redis (`redis_repo.py`).
* **Rationale:** Enterprise deployments require seamless transitions between local development (SQLite), standard staging environments (PostgreSQL via SQLAlchemy), and managed cloud platforms (AWS DynamoDB + ElastiCache Redis). The abstract repository layer isolates core scoring logic from storage implementations.

## 2. Intent-Cluster Dual Baselines
* **Decision:** Use TF-IDF text vectorization and K-Means clustering to partition the 50 synthetic scenarios into intent clusters (e.g., Data Retrieval, System Mutation, External Alerting).
* **Rationale:** A global overall baseline compares every query against the average of all possible tools. This causes legitimate but complex queries (such as a database deletion request) to yield high cosine distance when evaluated against an overall baseline containing read queries. Clustering queries by intent ensures live requests are matched against their corresponding sub-baseline first, eliminating false positive alerts.

## 3. Directed Markov Tool Transition Graph & Hijack Detection
* **Decision:** Model execution flows as a directed graph $P(T_{\text{next}} \mid T_{\text{current}})$. If a live sequence contains an unseen transition ($P = 0.0$), force a Markov penalty of `1.0` and boost the overall anomaly score to at least `0.75` (Severe Anomaly / Alert tier).
* **Rationale:** Parameter values can easily be crafted to appear benign while an adversary hijacks control flow (e.g., calling `delete_user` directly without preceding `read_user` or authorization checks). Transition probability enforcement catches control-flow hijacking regardless of parameter appearance.

## 4. Markov Penalty Normalization
* **Decision:** Average the surprise penalties ($1.0 - P$) for allowed transitions ($P > 0.0$) across the execution path, rather than taking the maximum penalty.
* **Rationale:** Taking the maximum penalty for allowed normal branches caused common operational choices (such as choosing between an update vs deletion) to yield false warnings (>0.30). Averaging allowed transition surprise prevents normal branching from inflating scores, while unexpected transitions ($P = 0.0$) still immediately trigger Severe Anomaly Alerts.

## 5. Visual Palette & Forensics Dashboard Identity
* **Decision:** Implement custom Streamlit CSS injecting the exact token palette (`--ink: #12141C`, `--paper: #E9E4D8`, `--signal: #3FE0C5`, `--alert-amber: #E8A23D`, `--alert-crimson: #D6413A`, `--graphite: #4A4E5C`) with JetBrains Mono monospace readouts, a persistent header fingerprint glyph, and a streaming seismograph line chart with 3 distinct horizontal health bands.
* **Rationale:** Avoid generic SaaS dashboard aesthetic; enforce a forensic laboratory console theme designed specifically around behavioral monitoring and seismographic anomaly detection.
