import random
import logging
from typing import List, Dict, Any, Tuple
import numpy as np
import app.database as database

logger = logging.getLogger("agent_baseline.profiler")

class SandboxProfiler:
    """Simulates agent execution in an isolated sandbox and records behavioral fingerprints."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    def simulate_execution(self, scenario: Dict[str, Any]) -> Tuple[List[str], List[int], int]:
        """Runs scenario through mock execution pipeline dynamically supporting any custom agent tools."""
        query = scenario.get("query", "") if isinstance(scenario, dict) else str(scenario)
        expected_tools = scenario.get("expected_tools", []) if isinstance(scenario, dict) else []
        query_lower = query.lower()

        tool_calls = []
        param_lengths = []

        def add_call(tool_name: str, base_len: int = 30):
            tool_calls.append(tool_name)
            param_lengths.append(max(5, int(np.random.normal(base_len, max(2, base_len * 0.2)))))

        def rand_choice(prob: float) -> bool:
            return random.random() < prob

        # 1. Direct match if scenario explicitly specifies expected tools
        if expected_tools:
            for t in expected_tools:
                add_call(t, random.randint(20, 50))
        else:
            # 2. Fetch agent's defined tools from DB dynamically
            agent_data = database.get_agent(self.agent_id)
            defined_tools = [t["name"] for t in agent_data.get("tools", [])] if agent_data else []

            if defined_tools:
                # Select primary tool based on query or pick first
                primary = defined_tools[0]
                add_call(primary, 25)

                for secondary in defined_tools[1:]:
                    if any(w in query_lower for w in secondary.split('_')) or rand_choice(0.4):
                        add_call(secondary, 35)
            else:
                add_call("read_data", 20)
                add_call("log_audit", 45)

        base_resp_len = 150
        if "delete" in query_lower or "purge" in query_lower:
            base_resp_len = 80
        elif "audit" in query_lower or "scan" in query_lower:
            base_resp_len = 220

        resp_len = max(20, int(np.random.normal(base_resp_len, base_resp_len * 0.25)))
        return tool_calls, param_lengths, resp_len

    def compute_fingerprint(self, traces: List[Tuple[List[str], List[int], int]]) -> Dict[str, Any]:
        """Calculates Tool Call Matrix, Directed Markov Graph, Parameter Bounds, and Response Lengths."""
        total_runs = len(traces)
        if total_runs == 0:
            return {}

        all_tools = set()
        tool_counts: Dict[str, int] = {}
        markov_counts: Dict[str, Dict[str, int]] = {}
        param_lens_per_tool: Dict[str, List[int]] = {}

        all_param_lens: List[int] = []
        all_resp_lens: List[int] = []
        all_tool_counts: List[int] = []

        for tool_calls, param_lens, resp_len in traces:
            all_tool_counts.append(len(tool_calls))
            all_resp_lens.append(resp_len)
            all_param_lens.extend(param_lens)

            seq = ["[START]"] + tool_calls + ["[END]"]

            for t in tool_calls:
                all_tools.add(t)
                tool_counts[t] = tool_counts.get(t, 0) + 1

            for t, p_len in zip(tool_calls, param_lens):
                if t not in param_lens_per_tool:
                    param_lens_per_tool[t] = []
                param_lens_per_tool[t].append(p_len)

            for i in range(len(seq) - 1):
                curr_t = seq[i]
                next_t = seq[i+1]
                all_tools.add(curr_t)
                all_tools.add(next_t)

                if curr_t not in markov_counts:
                    markov_counts[curr_t] = {}
                markov_counts[curr_t][next_t] = markov_counts[curr_t].get(next_t, 0) + 1

        total_invocations = sum(tool_counts.values()) or 1
        tool_frequency = {t: tool_counts.get(t, 0) / total_invocations for t in sorted(all_tools) if not t.startswith("[")}

        markov_transitions: Dict[str, Dict[str, float]] = {}
        for curr_t, next_dict in markov_counts.items():
            row_total = sum(next_dict.values())
            markov_transitions[curr_t] = {nxt: count / row_total for nxt, count in next_dict.items()}

        per_tool_bounds = {}
        for t, lens in param_lens_per_tool.items():
            per_tool_bounds[t] = {
                "mean": float(np.mean(lens)) if lens else 0.0,
                "std": float(np.std(lens)) if lens else 1.0
            }

        return {
            "sample_size": total_runs,
            "tool_frequency": tool_frequency,
            "markov_transitions": markov_transitions,
            "metrics_bounds": {
                "parameter_length": {
                    "mean": float(np.mean(all_param_lens)) if all_param_lens else 0.0,
                    "std": float(np.std(all_param_lens)) if all_param_lens else 1.0
                },
                "response_length": {
                    "mean": float(np.mean(all_resp_lens)) if all_resp_lens else 0.0,
                    "std": float(np.std(all_resp_lens)) if all_resp_lens else 1.0
                },
                "tool_call_count": {
                    "mean": float(np.mean(all_tool_counts)) if all_tool_counts else 0.0,
                    "std": float(np.std(all_tool_counts)) if all_tool_counts else 1.0
                }
            },
            "per_tool_bounds": per_tool_bounds,
            "data_access_scope": sorted(list(all_tools - {"[START]", "[END]"}))
        }

    def profile_scenarios(self, scenarios: List[Dict[str, Any]], cluster_labels: List[int], num_clusters: int = 3) -> Dict[int, Dict[str, Any]]:
        """Profiles scenarios across overall baseline (-1) and each intent cluster."""
        all_traces = [self.simulate_execution(s) for s in scenarios]
        overall_fingerprint = self.compute_fingerprint(all_traces)
        database.save_baseline(self.agent_id, -1, overall_fingerprint)

        cluster_fingerprints = {-1: overall_fingerprint}

        for c_id in range(num_clusters):
            c_indices = [i for i, label in enumerate(cluster_labels) if label == c_id]
            c_traces = [all_traces[i] for i in c_indices]
            if c_traces:
                c_fingerprint = self.compute_fingerprint(c_traces)
                database.save_baseline(self.agent_id, c_id, c_fingerprint)
                cluster_fingerprints[c_id] = c_fingerprint

        return cluster_fingerprints
