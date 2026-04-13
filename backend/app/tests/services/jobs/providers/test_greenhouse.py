import pytest
import httpx

from app.services.jobs.providers.greenhouse import GreenhouseJobBoardProvider
from app.core.config import get_settings


@pytest.mark.asyncio
async def test_fetch_jobs_success(monkeypatch):
    """Greenhouse returns jobs and they get normalized."""

    mock_response = {
        "jobs": [
            {
                "id": 123,
                "title": "Software Engineer I",
                "absolute_url": "https://example.com/job/123",
                "content": "<p>Build stuff</p>",
                "location": {"name": "United States"},
                "metadata": [],
            }
        ],
        "meta": {"total": 1},
    }

    async def mock_get(*args, **kwargs):
        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return mock_response

        return MockResponse()

    provider = GreenhouseJobBoardProvider(board_tokens=["stripe"])

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    jobs = await provider.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].title == "Software Engineer I"
    assert jobs[0].company is not None


@pytest.mark.asyncio
async def test_fetch_jobs_handles_404(monkeypatch):
    """Invalid board tokens should not crash provider."""

    async def mock_get(*args, **kwargs):
        request = httpx.Request("GET", "https://test")
        response = httpx.Response(404, request=request)
        raise httpx.HTTPStatusError("404", request=request, response=response)

    provider = GreenhouseJobBoardProvider(board_tokens=["badtoken"])

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    jobs = await provider.fetch_jobs()

    assert jobs == []


def test_from_env_disabled(monkeypatch):
    """Provider should not initialize if disabled."""

    monkeypatch.setenv("JOB_PROVIDER_GREENHOUSE_ENABLED", "false")
    monkeypatch.setenv("JOB_PROVIDER_GREENHOUSE_BOARD_TOKENS", "stripe")

    provider = GreenhouseJobBoardProvider.from_env()

    assert provider is None


def test_from_env_enabled(monkeypatch):
    """Provider should initialize when enabled and tokens exist."""

    monkeypatch.setenv("JOB_PROVIDER_GREENHOUSE_ENABLED", "true")
    monkeypatch.setenv("JOB_PROVIDER_GREENHOUSE_BOARD_TOKENS", "stripe,figma")

    # 🔥 THIS IS THE FIX
    get_settings.cache_clear()

    provider = GreenhouseJobBoardProvider.from_env()

    assert provider is not None
    assert provider.board_tokens == ["stripe", "figma"]