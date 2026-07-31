import pytest
from app.scenario_generator.generator import generate_procedural_scenarios, cluster_scenarios
from app.profiler.profiler import SandboxProfiler
from app import database

TEST_TOOLS = [
    {"name": "read_user", "description": "Fetch user details"},
    {"name": "update_user_status", "description": "Update status"},
    {"name": "delete_user", "description": "Purge records"},
    {"name": "send_email", "description": "Email alerts"},
    {"name": "log_audit", "description": "Audit logging"}
]

def test_profiler_fingerprint_generation():
    database.init_db()
    database.save_agent(
        agent_id="test_profiler_agent",
        name="Test Profiler Agent",
        description="Agent for testing profiler",
        system_prompt="Manage database accounts",
        tools=TEST_TOOLS
    )

    scenarios = generate_procedural_scenarios("test_profiler_agent", "Test prompt", TEST_TOOLS)
    clustering = cluster_scenarios(scenarios, num_clusters=3)

    profiler = SandboxProfiler("test_profiler_agent")
    baselines = profiler.profile_scenarios(scenarios, clustering["labels"], num_clusters=3)

    assert -1 in baselines
    assert 0 in baselines
    assert "tool_frequency" in baselines[-1]
    assert "markov_transitions" in baselines[-1]
    assert "metrics_bounds" in baselines[-1]
    assert baselines[-1]["sample_size"] == 50
