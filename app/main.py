from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.ai_client import AIClient, AIClientError
from app.config import AISettings
from app.models import AgentChatRequest, TaskResponse, TextRequest
from app.services import run_agent, run_style, run_syntax, run_word_choice


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = AISettings.from_env()
    app.state.settings = settings
    app.state.ai_client = AIClient(settings) if settings.is_ready() else None
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


@app.get("/health")
async def health() -> dict:
    settings: AISettings = app.state.settings
    return {
        "status": "ok",
        "ai_configured": app.state.ai_client is not None,
        "config": settings.redacted(),
    }


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


@app.post("/agent/chat", response_model=TaskResponse)
async def agent_chat(
    request: AgentChatRequest,
    client: AIClient = Depends(get_client),
) -> TaskResponse:
    return await _handle_task(run_agent(client, request))


async def _handle_task(coro) -> TaskResponse:
    try:
        return await coro
    except AIClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=502, detail=exc.errors()) from exc
