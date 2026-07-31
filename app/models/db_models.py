import json
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class AgentModel(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=False)
    tools = Column(Text, nullable=False)  # JSON serialized string
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())

class BaselineModel(Base):
    __tablename__ = "baselines"

    agent_id = Column(String, primary_key=True)
    cluster_id = Column(Integer, primary_key=True)  # -1 for overall baseline
    fingerprint = Column(Text, nullable=False)       # JSON serialized string
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())

class IntentClusterModel(Base):
    __tablename__ = "intent_clusters"

    agent_id = Column(String, primary_key=True)
    cluster_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    keywords = Column(Text, nullable=False)          # JSON serialized string
    size = Column(Integer, nullable=False)

class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    agent_id = Column(String, nullable=False, index=True)
    query = Column(Text, nullable=False)
    cluster_id = Column(Integer, nullable=False)
    tool_calls = Column(Text, nullable=False)        # JSON serialized string
    metrics = Column(Text, nullable=False)           # JSON serialized string
    anomaly_score = Column(Float, nullable=False)
    health_tier = Column(String, nullable=False)     # normal, warning, alert
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())

class DriftAlertModel(Base):
    __tablename__ = "drift_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, nullable=False, index=True)
    message = Column(Text, nullable=False)
    score = Column(Float, nullable=False)
    status = Column(String, default="pending")       # pending, refreshed
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
