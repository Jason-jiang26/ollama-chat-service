"""A small local chat API. Start with: python -m uvicorn main:app --reload."""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Literal

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = "http://127.0.0.1:11434"
    model: str = "gemma3:270m"
    request_timeout: float = 120.0

    @classmethod
    def from_environment(cls) -> "Settings":
        timeout = float(os.getenv("CHAT_TIMEOUT_SECONDS", "120"))
        if not 1 <= timeout <= 600:
            raise ValueError("CHAT_TIMEOUT_SECONDS must be between 1 and 600")
        model = os.getenv("OLLAMA_MODEL", "gemma3:270m").strip()
        if not model:
            raise ValueError("OLLAMA_MODEL must not be empty")
        return cls(
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            model=model,
            request_timeout=timeout,
        )


# Strict validation rejects numbers, blank messages, and overly long inputs.
MessageText = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=4000)
]


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: MessageText


class ChatReply(BaseModel):
    model: str
    reply: str


class HealthReply(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyReply(BaseModel):
    status: Literal["ready"] = "ready"
    model: str


class UpstreamMessage(BaseModel):
    content: str


class UpstreamChatReply(BaseModel):
    message: UpstreamMessage


class InstalledModel(BaseModel):
    name: str


class ModelList(BaseModel):
    models: list[InstalledModel]


class OllamaBackend:
    """Use Ollama's HTTP API through a reusable asynchronous client."""

    def __init__(self, client: httpx.AsyncClient, settings: Settings):
        self.client = client
        self.settings = settings

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = await asyncio.wait_for(
                self.client.request(method, path, **kwargs),
                timeout=self.settings.request_timeout,
            )
            response.raise_for_status()
            return response.json()
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise HTTPException(504, "Ollama 响应超时，请稍后重试。") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise HTTPException(503, "模型或 Ollama 接口未找到，请检查模型是否已下载。") from exc
            raise HTTPException(502, "Ollama 返回了错误响应。") from exc
        except httpx.ConnectError as exc:
            raise HTTPException(503, "无法连接 Ollama，请先启动本地 Ollama 服务。") from exc
        except httpx.RequestError as exc:
            raise HTTPException(502, "与 Ollama 通信失败。") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise HTTPException(502, "Ollama 返回了无法解析的响应。") from exc

    async def ready(self) -> None:
        payload = await self._request("GET", "/api/tags")
        try:
            installed = ModelList.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(502, "Ollama 模型列表格式不正确。") from exc
        if self.settings.model not in {model.name for model in installed.models}:
            raise HTTPException(503, "配置的模型尚未下载，请先执行 ollama pull。")

    async def chat(self, message: str) -> str:
        payload = await self._request(
            "POST",
            "/api/chat",
            json={
                "model": self.settings.model,
                "messages": [{"role": "user", "content": message}],
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 256, "num_ctx": 2048},
            },
        )
        try:
            reply = UpstreamChatReply.model_validate(payload).message.content.strip()
        except ValidationError as exc:
            raise HTTPException(502, "Ollama 对话响应格式不正确。") from exc
        if not reply:
            raise HTTPException(502, "Ollama 返回了空回复。")
        return reply


def create_app(
    settings: Settings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    settings = settings or Settings.from_environment()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # Local requests bypass system proxies, so Clash settings do not
        # interfere with FastAPI -> Ollama connections.
        async with httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=httpx.Timeout(settings.request_timeout, connect=5.0),
            trust_env=False,
            transport=transport,
        ) as client:
            application.state.backend = OllamaBackend(client, settings)
            yield

    application = FastAPI(
        title="姜杰中的本地AI聊天服务",
        description="基于 FastAPI 和 Ollama 的本地单轮对话 API。",
        version="0.1.0",
        lifespan=lifespan,
    )

    @application.get("/health", response_model=HealthReply)
    async def health() -> HealthReply:
        """Only check whether this FastAPI process is responding."""
        return HealthReply()

    @application.get("/ready", response_model=ReadyReply)
    async def ready(request: Request) -> ReadyReply:
        """Check Ollama connectivity and the configured model's presence."""
        await request.app.state.backend.ready()
        return ReadyReply(model=settings.model)

    @application.post(
        "/chat",
        response_model=ChatReply,
        responses={
            502: {"description": "Ollama 通信或响应异常"},
            503: {"description": "Ollama 或模型不可用"},
            504: {"description": "Ollama 响应超时"},
        },
    )
    async def chat_endpoint(body: ChatRequest, request: Request) -> ChatReply:
        reply = await request.app.state.backend.chat(body.message)
        return ChatReply(model=settings.model, reply=reply)

    @application.get("/info")
    async def info() -> dict[str, str]:
        return {
            "service": application.title,
            "model": settings.model,
        }

    return application


app = create_app()
