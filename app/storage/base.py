from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class BaseAgentRepository(ABC):
    @abstractmethod
    def save_agent(self, agent_id: str, name: str, description: str, system_prompt: str, tools: list):
        pass

    @abstractmethod
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def list_agents(self) -> List[Dict[str, Any]]:
        pass


class BaseBaselineRepository(ABC):
    @abstractmethod
    def save_baseline(self, agent_id: str, cluster_id: int, fingerprint: dict):
        pass

    @abstractmethod
    def get_baseline(self, agent_id: str, cluster_id: int) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_all_baselines(self, agent_id: str) -> Dict[int, Dict[str, Any]]:
        pass


class BaseIntentClusterRepository(ABC):
    @abstractmethod
    def save_intent_clusters(self, agent_id: str, clusters: list):
        pass

    @abstractmethod
    def get_intent_clusters(self, agent_id: str) -> List[Dict[str, Any]]:
        pass


class BaseSessionRepository(ABC):
    @abstractmethod
    def save_session(self, session_id: str, agent_id: str, query: str, cluster_id: int, tool_calls: list, metrics: dict, anomaly_score: float, health_tier: str):
        pass

    @abstractmethod
    def get_sessions(self, agent_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        pass


class BaseDriftAlertRepository(ABC):
    @abstractmethod
    def save_drift_alert(self, agent_id: str, message: str, score: float):
        pass

    @abstractmethod
    def get_active_drift_alerts(self, agent_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def resolve_drift_alerts(self, agent_id: str):
        pass
