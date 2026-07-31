import pytest
from app.drift_detector import DriftDetector, trigger_baseline_refresh
from app import database

TEST_TOOLS = [
    {"name": "read_user", "description": "Fetch user details"},
    {"name": "update_user_status", "description": "Update status"},
    {"name": "delete_user", "description": "Purge records"},
    {"name": "send_email", "description": "Email alerts"},
    {"name": "log_audit", "description": "Audit logging"}
]

def test_drift_detector_and_refresh():
    database.init_db()
    agent_id = "test_drift_agent"
    database.save_agent(
        agent_id=agent_id,
        name="Drift Test Agent",
        description="Testing drift detection",
        system_prompt="Manage database and operations",
        tools=TEST_TOOLS
    )

    # 1. Populate sliding window with elevated anomaly scores (simulating prompt/model swap drift)
    for i in range(10):
        database.redis_cache_session(agent_id, {
            "session_id": f"sess_{i}",
            "anomaly_score": 0.45,
            "metrics": {"tool_frequency_distance": 0.30}
        })

    detector = DriftDetector(agent_id, window_size=10, drift_threshold=0.35)
    res = detector.evaluate_recent_window()

    assert res["drifted"] is True
    assert res["average_anomaly"] >= 0.35

    alerts = database.get_active_drift_alerts(agent_id)
    assert len(alerts) > 0

    # 2. Trigger automated refresh
    refresh_res = trigger_baseline_refresh(agent_id)
    assert refresh_res["status"] == "success"

    active_after = database.get_active_drift_alerts(agent_id)
    assert len(active_after) == 0
