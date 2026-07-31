import json
import logging
from typing import List, Dict, Any, Optional
import app.config as config

logger = logging.getLogger("agent_baseline.storage.redis")

# Global in-memory fallback if Redis connection is unavailable
_memory_session_cache: Dict[str, List[dict]] = {}

class RedisSessionRepository:
    def __init__(self):
        self.redis_client = None
        if getattr(config, "REDIS_HOST", None):
            try:
                import redis
                self.redis_client = redis.Redis(
                    host=config.REDIS_HOST,
                    port=getattr(config, "REDIS_PORT", 6379),
                    db=0,
                    decode_responses=True,
                    socket_timeout=2
                )
                self.redis_client.ping()
                logger.info(f"Connected to Redis session cache at {config.REDIS_HOST}")
            except Exception as e:
                logger.warning(f"Could not connect to Redis ({e}). Falling back to in-memory session cache.")
                self.redis_client = None

    def cache_session(self, agent_id: str, session_data: dict, max_window: int = 100):
        if self.redis_client:
            try:
                key = f"agent_sessions:{agent_id}"
                self.redis_client.lpush(key, json.dumps(session_data))
                self.redis_client.ltrim(key, 0, max_window - 1)
                return
            except Exception as e:
                logger.warning(f"Redis cache push failed: {e}")

        # In-memory fallback
        if agent_id not in _memory_session_cache:
            _memory_session_cache[agent_id] = []
        _memory_session_cache[agent_id].insert(0, session_data)
        if len(_memory_session_cache[agent_id]) > max_window:
            _memory_session_cache[agent_id] = _memory_session_cache[agent_id][:max_window]

    def get_recent_sessions(self, agent_id: str, limit: int = 50) -> List[dict]:
        if self.redis_client:
            try:
                key = f"agent_sessions:{agent_id}"
                raw = self.redis_client.lrange(key, 0, limit - 1)
                return [json.loads(item) for item in raw]
            except Exception as e:
                logger.warning(f"Redis fetch failed: {e}")

        # In-memory fallback
        return _memory_session_cache.get(agent_id, [])[:limit]
