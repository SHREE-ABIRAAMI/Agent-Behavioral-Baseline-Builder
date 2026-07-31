import logging
from app.storage.postgres_repo import SQLAlchemyRepository
from app.storage.redis_repo import RedisSessionRepository

logger = logging.getLogger("agent_baseline.database")

# Initialize global repository instances
repo = SQLAlchemyRepository()
redis_repo = RedisSessionRepository()

def init_db():
    pass # Managed in SQLAlchemyRepository __init__

# Agent delegation
def save_agent(agent_id: str, name: str, description: str, system_prompt: str, tools: list):
    repo.save_agent(agent_id, name, description, system_prompt, tools)

def get_agent(agent_id: str):
    return repo.get_agent(agent_id)

def list_agents():
    return repo.list_agents()

# Baseline delegation
def save_baseline(agent_id: str, cluster_id: int, fingerprint: dict):
    repo.save_baseline(agent_id, cluster_id, fingerprint)

def get_baseline(agent_id: str, cluster_id: int):
    return repo.get_baseline(agent_id, cluster_id)

def get_all_baselines(agent_id: str):
    return repo.get_all_baselines(agent_id)

# Intent cluster delegation
def save_intent_clusters(agent_id: str, clusters: list):
    repo.save_intent_clusters(agent_id, clusters)

def get_intent_clusters(agent_id: str):
    return repo.get_intent_clusters(agent_id)

# Session delegation
def save_session(session_id: str, agent_id: str, query: str, cluster_id: int, tool_calls: list, metrics: dict, anomaly_score: float, health_tier: str):
    repo.save_session(session_id, agent_id, query, cluster_id, tool_calls, metrics, anomaly_score, health_tier)

def get_sessions(agent_id: str, limit: int = 100):
    return repo.get_sessions(agent_id, limit)

# Redis session caching delegation
def redis_cache_session(agent_id: str, session_data: dict, max_window: int = 100):
    redis_repo.cache_session(agent_id, session_data, max_window)

def redis_get_recent_sessions(agent_id: str, limit: int = 50):
    return redis_repo.get_recent_sessions(agent_id, limit)

# Drift alert delegation
def save_drift_alert(agent_id: str, message: str, score: float):
    repo.save_drift_alert(agent_id, message, score)

def get_active_drift_alerts(agent_id: str):
    return repo.get_active_drift_alerts(agent_id)

def resolve_drift_alerts(agent_id: str):
    repo.resolve_drift_alerts(agent_id)
