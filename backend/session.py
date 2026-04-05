import uuid
from datetime import datetime, timedelta
from typing import Optional

SYSTEM_PROMPT = """You are an observability assistant integrated with DataDog running on Azure infrastructure.

You help engineers:
- Query and analyse metrics, logs, and traces
- Check monitor and alert status
- Investigate incidents and anomalies
- Summarise service health and SLOs
- Correlate events across services

Guidelines:
- Be concise but thorough
- Format metrics and data in readable tables or lists
- Highlight anything that looks like an active incident or degradation
- When asked about a service, check both metrics and recent logs
- Always state the time window you queried
"""


class SessionStore:
    """
    In-memory session store with TTL-based expiry.
    For production at scale, replace with Redis.
    """

    def __init__(self, ttl_minutes: int = 60):
        self._sessions: dict[str, dict] = {}
        self.ttl = timedelta(minutes=ttl_minutes)

    def create(self) -> str:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "history": [{"role": "system", "content": SYSTEM_PROMPT}],
            "created_at": datetime.utcnow(),
            "last_active": datetime.utcnow()
        }
        return session_id

    def get(self, session_id: str) -> Optional[list]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        if datetime.utcnow() - session["last_active"] > self.ttl:
            del self._sessions[session_id]
            return None
        session["last_active"] = datetime.utcnow()
        return session["history"]

    def update(self, session_id: str, history: list):
        if session_id in self._sessions:
            self._sessions[session_id]["history"] = history
            self._sessions[session_id]["last_active"] = datetime.utcnow()

    def delete(self, session_id: str):
        self._sessions.pop(session_id, None)

    def clear_expired(self):
        now = datetime.utcnow()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s["last_active"] > self.ttl
        ]
        for sid in expired:
            del self._sessions[sid]
