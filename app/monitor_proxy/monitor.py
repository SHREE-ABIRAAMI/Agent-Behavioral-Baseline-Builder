import logging
import numpy as np
from scipy.spatial.distance import cosine
from typing import List, Dict, Any, Tuple
import app.database as database
from app.scenario_generator.generator import load_clustering_models

logger = logging.getLogger("agent_baseline.monitor")

class TelemetryMonitor:
    """Production monitor proxy evaluating live execution spans against Intent-Cluster Baselines."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    def map_query_to_cluster(self, query: str) -> int:
        """Embeds query and predicts nearest K-Means intent cluster centroid."""
        models = load_clustering_models(self.agent_id)
        if models:
            vectorizer = models["vectorizer"]
            kmeans = models["kmeans"]
            try:
                X = vectorizer.transform([query])
                cluster_id = int(kmeans.predict(X)[0])
                return cluster_id
            except Exception as e:
                logger.warning(f"Failed predicting cluster for '{query}': {e}")
        return -1  # Fallback to overall baseline

    def get_baseline_fingerprint(self, cluster_id: int) -> Dict[str, Any]:
        """Loads cluster-specific baseline, falling back to overall baseline (-1) if missing."""
        fingerprint = database.get_baseline(self.agent_id, cluster_id)
        if fingerprint and "markov_transitions" in fingerprint and len(fingerprint["markov_transitions"]) > 0:
            return fingerprint
            
        overall = database.get_baseline(self.agent_id, -1)
        return fingerprint or overall or {}

    def _compute_frequency_distance(self, tool_calls: List[str], base_frequency: Dict[str, float]) -> float:
        """Computes Cosine Distance of relative tool invocation frequencies."""
        if not tool_calls or not base_frequency:
            return 0.0

        all_tools = sorted(list(set(tool_calls).union(set(base_frequency.keys()))))
        if not all_tools:
            return 0.0

        live_counts = {t: tool_calls.count(t) for t in all_tools}
        total_live = sum(live_counts.values()) or 1
        live_vec = np.array([live_counts[t] / total_live for t in all_tools])
        base_vec = np.array([base_frequency.get(t, 0.0) for t in all_tools])

        if np.all(live_vec == 0) or np.all(base_vec == 0):
            return 0.0

        try:
            d_cos = float(cosine(live_vec, base_vec))
            return 0.0 if np.isnan(d_cos) else d_cos
        except Exception:
            return 0.0

    def _compute_markov_anomaly(self, tool_calls: List[str], base_transitions: Dict[str, Dict[str, float]]) -> Tuple[float, List[dict]]:
        """Evaluates Directed Markov Graph. Unexpected transitions involving unregistered tools force a 1.0 hijack anomaly penalty."""
        if not base_transitions:
            return 0.0, []

        agent_data = database.get_agent(self.agent_id)
        registered_tools = set()
        if agent_data and "tools" in agent_data:
            for t in agent_data["tools"]:
                if isinstance(t, dict):
                    registered_tools.add(t.get("name"))
                elif isinstance(t, str):
                    registered_tools.add(t)

        # Include all tools present in baseline fingerprints
        for k, v in base_transitions.items():
            registered_tools.add(k)
            if isinstance(v, dict):
                for target in v.keys():
                    registered_tools.add(target)

        # Preset fallback tools
        registered_tools.update({"read_user", "fetch_account", "update_status", "audit_log", "purge_temp", "fetch_cve", "read_code", "apply_patch", "run_tests", "deploy_service"})
        registered_tools.add("[START]")
        registered_tools.add("[END]")

        sequence = ["[START]"] + tool_calls + ["[END]"]
        penalties = []
        unexpected = []

        for i in range(len(sequence) - 1):
            curr_state = sequence[i]
            next_state = sequence[i+1]

            allowed_transitions = base_transitions.get(curr_state, {})
            prob = allowed_transitions.get(next_state, 0.0)

            both_registered = (curr_state in registered_tools) and (next_state in registered_tools)

            if prob == 0.0:
                penalties.append(1.0)
                if not (curr_state == "[START]" and next_state == "[END]"):
                    unexpected.append({
                        "from_state": curr_state,
                        "to_state": next_state,
                        "probability": 0.0,
                        "description": f"Unexpected transition: '{curr_state}' ➔ '{next_state}' (Unobserved Sequence)"
                    })
            else:
                penalties.append(1.0 - prob)

        if not penalties:
            return 0.0, []

        if unexpected:
            markov_score = 1.0
        else:
            markov_score = float(np.mean(penalties))

        return markov_score, unexpected

    def _compute_bounds_anomaly(self, param_lengths: List[int], response_length: int, tool_count: int, base_bounds: Dict[str, Dict[str, float]]) -> Tuple[float, Dict[str, float]]:
        """Calculates Z-score deviations for parameter length, response length, and tool count."""
        if not base_bounds:
            return 0.0, {}

        z_scores = {}
        avg_param_len = float(np.mean(param_lengths)) if param_lengths else 0.0

        param_mean = base_bounds.get("parameter_length", {}).get("mean", 0.0)
        param_std = base_bounds.get("parameter_length", {}).get("std", 1.0) or 1.0
        z_scores["parameter_length"] = abs(avg_param_len - param_mean) / param_std

        resp_mean = base_bounds.get("response_length", {}).get("mean", 0.0)
        resp_std = base_bounds.get("response_length", {}).get("std", 1.0) or 1.0
        z_scores["response_length"] = abs(response_length - resp_mean) / resp_std

        count_mean = base_bounds.get("tool_call_count", {}).get("mean", 0.0)
        count_std = base_bounds.get("tool_call_count", {}).get("std", 1.0) or 1.0
        z_scores["tool_call_count"] = abs(tool_count - count_mean) / count_std

        max_z = max(z_scores.values()) if z_scores else 0.0
        bounds_score = min(1.0, max_z / 3.0)

        return float(bounds_score), z_scores

    def evaluate_execution(self, query: str, tool_calls: List[str], param_lengths: List[int], response_length: int) -> Dict[str, Any]:
        """Ingests live telemetry span and returns anomaly score & health tier."""
        cluster_id = self.map_query_to_cluster(query)
        fingerprint = self.get_baseline_fingerprint(cluster_id)

        base_freq = fingerprint.get("tool_frequency", {})
        base_transitions = fingerprint.get("markov_transitions", {})
        base_bounds = fingerprint.get("metrics_bounds", {})

        d_freq = self._compute_frequency_distance(tool_calls, base_freq)
        s_markov, unexpected = self._compute_markov_anomaly(tool_calls, base_transitions)
        s_bounds, z_scores = self._compute_bounds_anomaly(param_lengths, response_length, len(tool_calls), base_bounds)

        w_freq, w_markov, w_bounds = 0.25, 0.55, 0.20
        combined_score = (w_freq * d_freq) + (w_markov * s_markov) + (w_bounds * s_bounds)

        # Force severe alert if hijacked zero-probability transition occurred
        if unexpected:
            combined_score = max(combined_score, 0.75)

        combined_score = min(1.0, max(0.0, float(combined_score)))

        # Assign Health Tier
        if combined_score < 0.30:
            health_tier = "normal"
        elif combined_score < 0.70:
            health_tier = "warning"
        else:
            health_tier = "alert"

        metrics = {
            "tool_frequency_distance": d_freq,
            "markov_anomaly_score": s_markov,
            "bounds_anomaly_score": s_bounds,
            "z_scores": z_scores
        }

        return {
            "cluster_id": cluster_id,
            "anomaly_score": combined_score,
            "health_tier": health_tier,
            "metrics": metrics,
            "unexpected_transitions": unexpected
        }
