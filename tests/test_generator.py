import pytest
from app.scenario_generator.generator import (
    generate_scenarios, generate_procedural_scenarios, cluster_scenarios
)

TEST_TOOLS = [
    {"name": "read_user", "description": "Fetch user details"},
    {"name": "update_user_status", "description": "Update status"},
    {"name": "delete_user", "description": "Purge records"},
    {"name": "send_email", "description": "Email alerts"},
    {"name": "log_audit", "description": "Audit logging"}
]

def test_procedural_scenario_generation():
    scenarios = generate_procedural_scenarios("test_agent", "Test prompt", TEST_TOOLS)
    assert len(scenarios) == 50
    assert "scenario_id" in scenarios[0]
    assert "intent" in scenarios[0]
    assert "query" in scenarios[0]
    assert "expected_tools" in scenarios[0]

def test_kmeans_clustering():
    scenarios = generate_procedural_scenarios("test_agent", "Test prompt", TEST_TOOLS)
    res = cluster_scenarios(scenarios, num_clusters=3)
    assert "vectorizer" in res
    assert "kmeans" in res
    assert len(res["labels"]) == 50
    assert len(res["clusters"]) == 3
