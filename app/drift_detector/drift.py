import logging
import numpy as np
from typing import Dict, Any, List
import app.database as database

logger = logging.getLogger("agent_baseline.drift")

class DriftDetector:
    """Aggregates telemetry metrics across sliding production window to detect systemic model/prompt drift."""

    def __init__(self, agent_id: str, window_size: int = 15, drift_threshold: float = 0.35):
        self.agent_id = agent_id
        self.window_size = window_size
        self.drift_threshold = drift_threshold

    def evaluate_recent_window(self) -> Dict[str, Any]:
        """Calculates sliding window averages and triggers Baseline Drift Alert on sustained divergence."""
        sessions = database.redis_get_recent_sessions(self.agent_id, self.window_size)
        if not sessions or len(sessions) < 5:
            return {"drifted": False, "reason": "Insufficient sessions for sliding window analytics"}

        scores = [s.get("anomaly_score", 0.0) for s in sessions]
        freq_divs = [s.get("metrics", {}).get("tool_frequency_distance", 0.0) for s in sessions]

        avg_score = float(np.mean(scores))
        avg_freq_div = float(np.mean(freq_divs))

        # Check for sustained elevation in baseline divergence
        if avg_score >= self.drift_threshold or avg_freq_div >= 0.25:
            msg = f"Sustained behavioral drift detected across last {len(sessions)} runs (Avg Score: {avg_score:.2f}, Avg Freq Shift: {avg_freq_div:.2f})."
            database.save_drift_alert(self.agent_id, msg, avg_score)
            logger.warning(f"DRIFT ALERT: {msg}")
            return {
                "drifted": True,
                "average_anomaly": avg_score,
                "frequency_drift": avg_freq_div,
                "message": msg
            }

        return {
            "drifted": False,
            "average_anomaly": avg_score,
            "frequency_drift": avg_freq_div
        }

def trigger_baseline_refresh(agent_id: str):
    """Executes automatic re-run of Module 1 + Module 2 to refresh zero-day baseline."""
    from app.scenario_generator import generate_scenarios, cluster_scenarios, save_clustering_models
    from app.profiler import SandboxProfiler

    agent = database.get_agent(agent_id)
    if not agent:
        return {"status": "error", "message": f"Agent {agent_id} not found."}

    logger.info(f"Auto-refreshing baseline for agent '{agent_id}'...")

    scenarios = generate_scenarios(agent_id, agent["system_prompt"], agent["tools"])
    clustering = cluster_scenarios(scenarios, num_clusters=3)
    save_clustering_models(agent_id, clustering["vectorizer"], clustering["kmeans"])

    profiler = SandboxProfiler(agent_id)
    baselines = profiler.profile_scenarios(scenarios, clustering["labels"], num_clusters=3)
    database.save_intent_clusters(agent_id, clustering["clusters"])

    database.resolve_drift_alerts(agent_id)
    logger.info(f"Baseline for '{agent_id}' successfully recalibrated.")

    return {
        "status": "success",
        "agent_id": agent_id,
        "scenarios_count": len(scenarios),
        "clusters_count": len(clustering["clusters"])
    }
