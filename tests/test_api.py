"""Offline API tests: no model download, GPU, or running Ollama is required."""
import httpx
import pytest
from fastapi.testclient import TestClient

from main import Settings, create_app


def client_with(handler):
    return TestClient(create_app(Settings(), transport=httpx.MockTransport(handler)))


def test_health_does_not_require_ollama():
    def offline(request):
        raise httpx.ConnectError("offline", request=request)

    with client_with(offline) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/ready").status_code == 503


def test_ready_checks_configured_model():
    def installed(request):
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [{"name": "gemma3:270m"}]})

    with client_with(installed) as client:
        assert client.get("/ready").json() == {"status": "ready", "model": "gemma3:270m"}


def test_ready_rejects_missing_model():
    with client_with(lambda request: httpx.Response(200, json={"models": []})) as client:
        assert client.get("/ready").status_code == 503


def test_ready_rejects_invalid_model_list():
    with client_with(lambda request: httpx.Response(200, json={"models": "wrong"})) as client:
        assert client.get("/ready").status_code == 502


def test_chat_sends_chinese_to_ollama_and_returns_reply():
    import json

    def chat(request):
        assert request.url.path == "/api/chat"
        body = json.loads(request.content)
        assert body["model"] == "gemma3:270m"
        assert body["messages"] == [{"role": "user", "content": "你好"}]
        assert body["stream"] is False
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "  你好！  "}})

    with client_with(chat) as client:
        response = client.post("/chat", json={"message": "  你好  "})
        assert response.status_code == 200
        assert response.json() == {"model": "gemma3:270m", "reply": "你好！"}


@pytest.mark.parametrize("payload", [
    {}, {"message": ""}, {"message": " \t\n "}, {"message": 123},
    {"message": None}, {"message": "a" * 4001},
    {"message": "hello", "model": "unapproved-model"},
])
def test_invalid_input_never_reaches_model(payload):
    def unexpected(request):
        pytest.fail("Invalid input reached Ollama")

    with client_with(unexpected) as client:
        assert client.post("/chat", json=payload).status_code == 422


@pytest.mark.parametrize("error_type,expected", [
    (httpx.ConnectError, 503), (httpx.ReadTimeout, 504),
    (httpx.RemoteProtocolError, 502),
])
def test_network_errors_have_actionable_status_codes(error_type, expected):
    def failure(request):
        raise error_type("simulated failure", request=request)

    with client_with(failure) as client:
        response = client.post("/chat", json={"message": "你好"})
        assert response.status_code == expected
        assert "detail" in response.json()


@pytest.mark.parametrize("upstream_status,expected", [(404, 503), (500, 502)])
def test_upstream_http_error_is_not_reported_as_success(upstream_status, expected):
    with client_with(lambda request: httpx.Response(upstream_status)) as client:
        assert client.post("/chat", json={"message": "hello"}).status_code == expected


@pytest.mark.parametrize("payload", [{}, {"message": {"content": " "}}, {"message": {"content": 123}}])
def test_bad_reply_is_rejected(payload):
    with client_with(lambda request: httpx.Response(200, json=payload)) as client:
        assert client.post("/chat", json={"message": "hello"}).status_code == 502


def test_non_json_reply_is_rejected():
    with client_with(lambda request: httpx.Response(200, text="not json")) as client:
        assert client.post("/chat", json={"message": "hello"}).status_code == 502
