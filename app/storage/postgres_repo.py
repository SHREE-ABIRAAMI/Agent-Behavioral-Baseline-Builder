import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import app.config as config
from app.models.db_models import (
    Base, AgentModel, BaselineModel, IntentClusterModel, SessionModel, DriftAlertModel
)
from app.storage.base import (
    BaseAgentRepository, BaseBaselineRepository, BaseIntentClusterRepository,
    BaseSessionRepository, BaseDriftAlertRepository
)

logger = logging.getLogger("agent_baseline.storage.postgres")

# Engine initialization
DATABASE_URL = getattr(config, "DATABASE_URL", None) or f"sqlite:///{config.DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def init_sqlalchemy_db():
    logger.info(f"Initializing database tables via SQLAlchemy at {DATABASE_URL}")
    Base.metadata.create_all(bind=engine)


class SQLAlchemyRepository(
    BaseAgentRepository,
    BaseBaselineRepository,
    BaseIntentClusterRepository,
    BaseSessionRepository,
    BaseDriftAlertRepository
):
    def __init__(self):
        init_sqlalchemy_db()

    def get_db(self):
        return SessionLocal()

    # Agent Operations
    def save_agent(self, agent_id: str, name: str, description: str, system_prompt: str, tools: list):
        session = self.get_db()
        try:
            agent = session.query(AgentModel).filter(AgentModel.id == agent_id).first()
            if not agent:
                agent = AgentModel(
                    id=agent_id,
                    name=name,
                    description=description,
                    system_prompt=system_prompt,
                    tools=json.dumps(tools)
                )
                session.add(agent)
            else:
                agent.name = name
                agent.description = description
                agent.system_prompt = system_prompt
                agent.tools = json.dumps(tools)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving agent: {e}")
            raise
        finally:
            session.close()

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        session = self.get_db()
        try:
            agent = session.query(AgentModel).filter(AgentModel.id == agent_id).first()
            if agent:
                return {
                    "id": agent.id,
                    "name": agent.name,
                    "description": agent.description,
                    "system_prompt": agent.system_prompt,
                    "tools": json.loads(agent.tools),
                    "created_at": agent.created_at
                }
        finally:
            session.close()
        return None

    def list_agents(self) -> List[Dict[str, Any]]:
        session = self.get_db()
        try:
            agents = session.query(AgentModel).all()
            return [
                {
                    "id": a.id,
                    "name": a.name,
                    "description": a.description,
                    "system_prompt": a.system_prompt,
                    "tools": json.loads(a.tools),
                    "created_at": a.created_at
                }
                for a in agents
            ]
        finally:
            session.close()

    # Baseline Operations
    def save_baseline(self, agent_id: str, cluster_id: int, fingerprint: dict):
        session = self.get_db()
        try:
            bl = session.query(BaselineModel).filter(
                BaselineModel.agent_id == agent_id,
                BaselineModel.cluster_id == cluster_id
            ).first()
            if not bl:
                bl = BaselineModel(
                    agent_id=agent_id,
                    cluster_id=cluster_id,
                    fingerprint=json.dumps(fingerprint)
                )
                session.add(bl)
            else:
                bl.fingerprint = json.dumps(fingerprint)
                bl.created_at = datetime.utcnow().isoformat()
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving baseline: {e}")
            raise
        finally:
            session.close()

    def get_baseline(self, agent_id: str, cluster_id: int) -> Optional[Dict[str, Any]]:
        session = self.get_db()
        try:
            bl = session.query(BaselineModel).filter(
                BaselineModel.agent_id == agent_id,
                BaselineModel.cluster_id == cluster_id
            ).first()
            if bl:
                return json.loads(bl.fingerprint)
        finally:
            session.close()
        return None

    def get_all_baselines(self, agent_id: str) -> Dict[int, Dict[str, Any]]:
        session = self.get_db()
        try:
            rows = session.query(BaselineModel).filter(BaselineModel.agent_id == agent_id).all()
            return {r.cluster_id: json.loads(r.fingerprint) for r in rows}
        finally:
            session.close()

    # Intent Cluster Operations
    def save_intent_clusters(self, agent_id: str, clusters: list):
        session = self.get_db()
        try:
            session.query(IntentClusterModel).filter(IntentClusterModel.agent_id == agent_id).delete()
            for c in clusters:
                cluster_obj = IntentClusterModel(
                    agent_id=agent_id,
                    cluster_id=c.get("cluster_id", 0),
                    name=c.get("name", c.get("intent", "Unknown")),
                    keywords=json.dumps(c.get("keywords", [])),
                    size=c.get("size", c.get("scenario_count", 0))
                )
                session.add(cluster_obj)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving intent clusters: {e}")
            raise
        finally:
            session.close()

    def get_intent_clusters(self, agent_id: str) -> List[Dict[str, Any]]:
        session = self.get_db()
        try:
            rows = session.query(IntentClusterModel).filter(IntentClusterModel.agent_id == agent_id).all()
            return [
                {
                    "cluster_id": r.cluster_id,
                    "name": r.name,
                    "keywords": json.loads(r.keywords),
                    "size": r.size
                }
                for r in rows
            ]
        finally:
            session.close()

    # Session Operations
    def save_session(self, session_id: str, agent_id: str, query: str, cluster_id: int, tool_calls: list, metrics: dict, anomaly_score: float, health_tier: str):
        session = self.get_db()
        try:
            sess = session.query(SessionModel).filter(SessionModel.id == session_id).first()
            if not sess:
                sess = SessionModel(
                    id=session_id,
                    agent_id=agent_id,
                    query=query,
                    cluster_id=cluster_id,
                    tool_calls=json.dumps(tool_calls),
                    metrics=json.dumps(metrics),
                    anomaly_score=anomaly_score,
                    health_tier=health_tier
                )
                session.add(sess)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving session: {e}")
            raise
        finally:
            session.close()

    def get_sessions(self, agent_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        session = self.get_db()
        try:
            rows = session.query(SessionModel).filter(
                SessionModel.agent_id == agent_id
            ).order_by(SessionModel.created_at.desc()).limit(limit).all()
            return [
                {
                    "id": r.id,
                    "agent_id": r.agent_id,
                    "query": r.query,
                    "cluster_id": r.cluster_id,
                    "tool_calls": json.loads(r.tool_calls),
                    "metrics": json.loads(r.metrics),
                    "anomaly_score": r.anomaly_score,
                    "health_tier": r.health_tier,
                    "created_at": r.created_at
                }
                for r in rows
            ]
        finally:
            session.close()

    # Drift Alert Operations
    def save_drift_alert(self, agent_id: str, message: str, score: float):
        session = self.get_db()
        try:
            alert = DriftAlertModel(
                agent_id=agent_id,
                message=message,
                score=score,
                status="pending"
            )
            session.add(alert)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving drift alert: {e}")
            raise
        finally:
            session.close()

    def get_active_drift_alerts(self, agent_id: str) -> List[Dict[str, Any]]:
        session = self.get_db()
        try:
            rows = session.query(DriftAlertModel).filter(
                DriftAlertModel.agent_id == agent_id,
                DriftAlertModel.status == "pending"
            ).order_by(DriftAlertModel.created_at.desc()).all()
            return [
                {
                    "id": r.id,
                    "agent_id": r.agent_id,
                    "message": r.message,
                    "score": r.score,
                    "status": r.status,
                    "created_at": r.created_at
                }
                for r in rows
            ]
        finally:
            session.close()

    def resolve_drift_alerts(self, agent_id: str):
        session = self.get_db()
        try:
            session.query(DriftAlertModel).filter(
                DriftAlertModel.agent_id == agent_id,
                DriftAlertModel.status == "pending"
            ).update({"status": "refreshed"})
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error resolving drift alerts: {e}")
            raise
        finally:
            session.close()
