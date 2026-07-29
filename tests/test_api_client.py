import asyncio

import httpx
import pytest

from app.services.api_client import (
    INTERNAL_SECRET_HEADER,
    InternalApiClient,
    InternalApiError,
    close_api_client,
    get_api_client,
)

SECRET = "test-internal-secret-value"


@pytest.fixture(autouse=True)
def _reset_singleton(monkeypatch):
    monkeypatch.setattr(
        "app.services.api_client.settings.INTERNAL_API_SECRET",
        SECRET,
    )
    yield
    asyncio.run(close_api_client())


def test_client_requires_secret(monkeypatch):
    monkeypatch.setattr("app.services.api_client.settings.INTERNAL_API_SECRET", "")
    with pytest.raises(RuntimeError, match="INTERNAL_API_SECRET"):
        InternalApiClient(secret="")


def test_post_injects_internal_secret_header():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["secret"] = request.headers.get(INTERNAL_SECRET_HEADER)
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"ok": True})

    async def _run() -> None:
        client = InternalApiClient(
            base_url="https://api.example.com",
            secret=SECRET,
            transport=httpx.MockTransport(handler),
        )
        response = await client.post("/citas/agendar", json={"fecha": "2026-08-01 10:00"})
        assert response.status_code == 200
        await client.aclose()

    asyncio.run(_run())
    assert captured["secret"] == SECRET
    assert "/citas/agendar" in captured["url"]


def test_secret_cannot_be_overridden_by_caller_headers():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["secret"] = request.headers.get(INTERNAL_SECRET_HEADER)
        return httpx.Response(200, json={"status": "ok"})

    async def _run() -> None:
        client = InternalApiClient(
            base_url="https://api.example.com",
            secret=SECRET,
            transport=httpx.MockTransport(handler),
        )
        await client.get("/health", headers={INTERNAL_SECRET_HEADER: "forged"})
        await client.aclose()

    asyncio.run(_run())
    assert captured["secret"] == SECRET


def test_401_raises_safe_error_without_secret():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "bad secret"})

    async def _run() -> None:
        client = InternalApiClient(
            base_url="https://api.example.com",
            secret=SECRET,
            transport=httpx.MockTransport(handler),
        )
        with pytest.raises(InternalApiError, match="autenticación") as exc_info:
            await client.post("/citas/agendar", json={})
        assert SECRET not in str(exc_info.value)
        assert exc_info.value.status_code == 401
        await client.aclose()

    asyncio.run(_run())


def test_403_and_500_map_to_safe_errors():
    async def _run() -> None:
        client = InternalApiClient(
            base_url="https://api.example.com",
            secret=SECRET,
            transport=httpx.MockTransport(lambda _r: httpx.Response(403)),
        )
        with pytest.raises(InternalApiError, match="denegó"):
            await client.get("/forbidden")
        await client.aclose()

        client = InternalApiClient(
            base_url="https://api.example.com",
            secret=SECRET,
            transport=httpx.MockTransport(lambda _r: httpx.Response(500)),
        )
        with pytest.raises(InternalApiError, match="error interno"):
            await client.get("/boom")
        await client.aclose()

    asyncio.run(_run())


def test_timeout_raises_safe_error():
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("x")

    async def _run() -> None:
        client = InternalApiClient(
            base_url="https://api.example.com",
            secret=SECRET,
            transport=httpx.MockTransport(handler),
        )
        with pytest.raises(InternalApiError, match="no respondió a tiempo") as exc_info:
            await client.get("/slow")
        assert SECRET not in str(exc_info.value)
        await client.aclose()

    asyncio.run(_run())


def test_connection_error_raises_safe_error():
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    async def _run() -> None:
        client = InternalApiClient(
            base_url="https://api.example.com",
            secret=SECRET,
            transport=httpx.MockTransport(handler),
        )
        with pytest.raises(InternalApiError, match="No se pudo conectar") as exc_info:
            await client.get("/down")
        assert SECRET not in str(exc_info.value)
        await client.aclose()

    asyncio.run(_run())


def test_get_api_client_singleton(monkeypatch):
    monkeypatch.setattr(
        "app.services.api_client.settings.CITAS_API_BASE_URL",
        "https://api.example.com",
    )

    async def _run() -> None:
        first = get_api_client(base_url="https://api.example.com")
        second = get_api_client()
        assert first is second
        await close_api_client()

    asyncio.run(_run())
