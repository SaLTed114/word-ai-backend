from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.ai_client import AIClient, AIClientError
from app.config import AISettings, PROJECT_ROOT, save_ai_settings
from app.context_builder import build_text_request_from_document
from app.models import (
    AIConfigUpdate,
    AIConfigView,
    AgentMessage,
    AgentSession,
    AgentSessionCreateRequest,
    AgentSessionMemory,
    AgentSessionMemoryUpdate,
    AgentSessionMessage,
    SkillContent,
    SkillCreate,
    SkillInfo,
    AgentSessionTurnRequest,
    AgentSessionTurnResponse,
    ContextBuildResult,
    DocumentContextRequest,
    TaskResponse,
    TextRequest,
)
from app.services import run_agent_turn, run_formula, run_style, run_syntax, run_word_choice
from app.storage import AgentSessionStore

SKILLS_DIR = PROJECT_ROOT / "skills"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = AISettings.from_env()
    session_store = AgentSessionStore()
    session_store.initialize()
    app.state.settings = settings
    app.state.ai_client = AIClient(settings) if settings.is_ready() else None
    app.state.session_store = session_store
    yield


app = FastAPI(
    title="Word AI Backend",
    description="HTTP API for the Word/WPS AI writing assistant backend prototype.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_client() -> AIClient:
    client = app.state.ai_client
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="AI client is not configured. Check .env and restart the server.",
        )
    return client


def get_session_store() -> AgentSessionStore:
    return app.state.session_store


@app.get("/health")
async def health() -> dict:
    settings: AISettings = app.state.settings
    return {
        "status": "ok",
        "ai_configured": app.state.ai_client is not None,
        "config": settings.redacted(),
    }


@app.get("/settings/ai-config", response_model=AIConfigView)
async def get_ai_config() -> AIConfigView:
    settings: AISettings = app.state.settings
    return AIConfigView(**settings.editable())


@app.put("/settings/ai-config", response_model=AIConfigView)
async def update_ai_config(request: AIConfigUpdate) -> AIConfigView:
    settings = save_ai_settings(
        api_key=request.api_key,
        model=request.model,
        base_url=request.base_url,
        api_endpoint=request.api_endpoint,
        proxy_url=request.proxy_url,
        trust_env=request.trust_env,
        use_json_mode=request.use_json_mode,
    )
    app.state.settings = settings
    app.state.ai_client = AIClient(settings) if settings.is_ready() else None
    return AIConfigView(**settings.editable())


@app.post("/tasks/syntax", response_model=TaskResponse)
async def syntax_task(
    request: TextRequest,
    client: AIClient = Depends(get_client),
) -> TaskResponse:
    return await _handle_task(run_syntax(client, request))


@app.post("/tasks/word-choice", response_model=TaskResponse)
async def word_choice_task(
    request: TextRequest,
    client: AIClient = Depends(get_client),
) -> TaskResponse:
    return await _handle_task(run_word_choice(client, request))


@app.post("/tasks/style", response_model=TaskResponse)
async def style_task(
    request: TextRequest,
    client: AIClient = Depends(get_client),
) -> TaskResponse:
    return await _handle_task(run_style(client, request))


@app.post("/tasks/formula", response_model=TaskResponse)
async def formula_task(
    request: TextRequest,
    client: AIClient = Depends(get_client),
) -> TaskResponse:
    return await _handle_task(run_formula(client, request))


@app.post("/context/build", response_model=ContextBuildResult)
async def build_context(request: DocumentContextRequest) -> ContextBuildResult:
    try:
        return build_text_request_from_document(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/agent/sessions", response_model=AgentSession)
async def create_agent_session(
    request: AgentSessionCreateRequest,
    store: AgentSessionStore = Depends(get_session_store),
) -> AgentSession:
    return store.create_session(title=request.title)


@app.get("/agent/sessions", response_model=list[AgentSession])
async def list_agent_sessions(
    limit: int = 50,
    store: AgentSessionStore = Depends(get_session_store),
) -> list[AgentSession]:
    return store.list_sessions(limit=limit)


@app.get("/agent/sessions/{session_id}", response_model=AgentSession)
async def get_agent_session(
    session_id: str,
    store: AgentSessionStore = Depends(get_session_store),
) -> AgentSession:
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent session not found.")
    return session


@app.delete("/agent/sessions/{session_id}")
async def delete_agent_session(
    session_id: str,
    store: AgentSessionStore = Depends(get_session_store),
) -> dict:
    deleted = store.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent session not found.")
    return {"deleted": True}


@app.get("/agent/sessions/{session_id}/messages", response_model=list[AgentSessionMessage])
async def list_agent_session_messages(
    session_id: str,
    limit: int = 50,
    store: AgentSessionStore = Depends(get_session_store),
) -> list[AgentSessionMessage]:
    _require_session(store, session_id)
    return store.list_messages(session_id=session_id, limit=limit)


@app.get("/agent/sessions/{session_id}/memory", response_model=AgentSessionMemory)
async def get_agent_session_memory(
    session_id: str,
    store: AgentSessionStore = Depends(get_session_store),
) -> AgentSessionMemory:
    _require_session(store, session_id)
    return store.get_memory(session_id)


@app.put("/agent/sessions/{session_id}/memory", response_model=AgentSessionMemory)
async def update_agent_session_memory(
    session_id: str,
    request: AgentSessionMemoryUpdate,
    store: AgentSessionStore = Depends(get_session_store),
) -> AgentSessionMemory:
    _require_session(store, session_id)
    return store.upsert_memory(session_id, request)


@app.post("/agent/sessions/{session_id}/messages", response_model=AgentSessionTurnResponse)
async def create_agent_session_message(
    session_id: str,
    request: AgentSessionTurnRequest,
    client: AIClient = Depends(get_client),
    store: AgentSessionStore = Depends(get_session_store),
) -> AgentSessionTurnResponse:
    session = _require_session(store, session_id)
    selection = _resolve_turn_selection(request)
    previous_messages = store.list_messages(session_id=session_id, limit=50)
    if not previous_messages and _needs_generated_title(session.title):
        store.update_session_title(session_id, _derive_session_title(request.message))
    history = _to_agent_history(previous_messages)
    memory = store.get_memory(session_id)
    user_message = store.add_message(
        session_id=session_id,
        role="user",
        content=request.message,
    )
    response = await _handle_task(
        run_agent_turn(
            client=client,
            message=request.message,
            selection=selection,
            history=history,
            memory=memory,
            skills=request.skills,
        )
    )
    assistant_message = store.add_message(
        session_id=session_id,
        role="assistant",
        content=response.reply,
        response=response,
    )
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent session not found.")
    return AgentSessionTurnResponse(
        session=session,
        user_message=user_message,
        assistant_message=assistant_message,
        response=response,
    )


@app.get("/skills", response_model=list[SkillInfo])
async def list_skills() -> list[SkillInfo]:
    if not SKILLS_DIR.exists():
        return []
    skills: list[SkillInfo] = []
    for path in sorted(SKILLS_DIR.glob("*.md")):
        skills.append(SkillInfo(name=path.stem, size=path.stat().st_size))
    return skills


@app.get("/skills/{name}", response_model=SkillContent)
async def get_skill(name: str) -> SkillContent:
    path = _skill_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found.")
    return SkillContent(name=name, content=path.read_text(encoding="utf-8"))


@app.post("/skills", response_model=SkillContent)
async def create_skill(request: SkillCreate) -> SkillContent:
    path = _skill_path(request.name)
    if path.exists():
        raise HTTPException(status_code=409, detail=f"Skill '{request.name}' already exists.")
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(request.content, encoding="utf-8")
    return SkillContent(name=request.name, content=request.content)


@app.put("/skills/{name}", response_model=SkillContent)
async def update_skill(name: str, request: SkillCreate) -> SkillContent:
    if name != request.name:
        old_path = _skill_path(name)
        if not old_path.exists():
            raise HTTPException(status_code=404, detail=f"Skill '{name}' not found.")
        old_path.unlink()
    path = _skill_path(request.name)
    path.write_text(request.content, encoding="utf-8")
    return SkillContent(name=request.name, content=request.content)


@app.delete("/skills/{name}")
async def delete_skill(name: str) -> dict:
    path = _skill_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found.")
    path.unlink()
    return {"deleted": True}


def _skill_path(name: str) -> Path:
    sanitized = name.strip().lower()
    if not sanitized or not all(c.isalnum() or c in "_-" for c in sanitized):
        raise HTTPException(status_code=400, detail="Invalid skill name.")
    return SKILLS_DIR / f"{sanitized}.md"


async def _handle_task(coro) -> TaskResponse:
    try:
        return await coro
    except AIClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=502, detail=exc.errors()) from exc


def _resolve_turn_selection(request: AgentSessionTurnRequest) -> TextRequest | None:
    if request.document_context is None:
        return request.selection
    try:
        return build_text_request_from_document(request.document_context).text_request
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _require_session(store: AgentSessionStore, session_id: str) -> AgentSession:
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent session not found.")
    return session


def _to_agent_history(messages: list[AgentSessionMessage]) -> list[AgentMessage]:
    return [
        AgentMessage(role=message.role, content=message.content)
        for message in messages
        if message.role in {"user", "assistant", "system"}
    ]


def _needs_generated_title(title: str | None) -> bool:
    if title is None:
        return True
    return title.strip().lower() in {"", "word-addin", "cli", "session"}


def _derive_session_title(message: str) -> str:
    compact = " ".join(message.split())
    if not compact:
        return "Session"
    limit = 24
    return compact if len(compact) <= limit else f"{compact[:limit].rstrip()}..."
