import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from agent import ObservabilityAgent
from session import SessionStore

load_dotenv()

agent = ObservabilityAgent()
sessions = SessionStore(ttl_minutes=60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await agent.connect()
    yield
    await agent.disconnect()


app = FastAPI(title="Observability Agent API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Models ───────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str

class ChatResponse(BaseModel):
    session_id: str
    response: str

class SessionResponse(BaseModel):
    session_id: str


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "tools_loaded": len(agent.tools),
        "tool_names": [t["function"]["name"] for t in agent.tools]
    }


@app.post("/session", response_model=SessionResponse)
def create_session():
    return {"session_id": sessions.create()}


@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    sessions.delete(session_id)
    return {"status": "deleted"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # Auto-create session if not provided or expired
    session_id = req.session_id
    history = sessions.get(session_id) if session_id else None

    if history is None:
        session_id = sessions.create()
        history = sessions.get(session_id)

    try:
        response, updated_history = await agent.chat(history, req.message)
        sessions.update(session_id, updated_history)
        return ChatResponse(session_id=session_id, response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
