"""Tests for production-grade LLM providers."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.generation.exceptions import (
    GenerationTimeoutError,
    LLMProviderUnavailableError,
)
from backend.generation.providers.base_provider import LLMProvider
from backend.generation.providers.common.http_client import HTTPProviderClient
from backend.generation.providers.openai_provider import (
    OpenAICompatibleProvider,
    OpenAICompatibleSettings,
)


@pytest.fixture
def mock_httpx_response():
    """Create a mock HTTP response."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "test-id",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "This is a test response. [doc_1] [doc_2]"
            }
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        "model": "gpt-3.5-turbo"
    }
    mock_response.aiter_text.return_value = async_iter(["This is a test response. [doc_1] [doc_2]"])
    return mock_response


def async_iter(items):
    """Create an async iterator from a list."""
    async def _async_gen():
        for item in items:
            yield item
    return _async_gen()


class TestOpenAICompatibleProvider:
    """Test suite for OpenAICompatibleProvider."""

    @pytest.fixture
    def provider(self):
        """Create a test provider instance."""
        return OpenAICompatibleProvider(
            model="gpt-3.5-turbo-test",
            base_url="http://localhost:8000/v1",
            api_key="test-key",
            timeout_s=30.0
        )

    @pytest.mark.asyncio
    async def test_provider_name(self, provider):
        """Test that provider name is correctly returned."""
        assert provider.provider_name == "openai_compatible"

    @pytest.mark.asyncio
    async def test_model_name(self, provider):
        """Test that model name is correctly returned."""
        assert provider.model_name == "gpt-3.5-turbo-test"

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, provider, mock_httpx_response):
        """Test health check when provider is healthy."""
        with patch.object(provider._http_client, 'health_check', AsyncMock(
            return_value={
                "status": "healthy",
                "status_code": 200,
                "latency_ms": 100,
                "data": {}
            }
        )):
            result = await provider.health_check()
            assert result["status"] == "healthy"
            assert result["status_code"] == 200
            assert result["latency_ms"] == 100

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, provider):
        """Test health check when provider is unhealthy."""
        with patch.object(provider._http_client, 'health_check', AsyncMock(
            return_value={
                "status": "unhealthy",
                "status_code": 500,
                "latency_ms": 500,
                "data": {"error": "Service unavailable"}
            }
        )):
            result = await provider.health_check()
            assert result["status"] == "unhealthy"
            assert result["status_code"] == 500

    @pytest.mark.asyncio
    async def test_generate_success(self, provider, mock_httpx_response):
        """Test successful generation."""
        with patch.object(provider._http_client, '_request_with_retry', AsyncMock(
            return_value=mock_httpx_response
        )):
            result = await provider.generate(
                prompt="Test prompt",
                temperature=0.2,
                max_tokens=512,
                timeout_s=60.0,
                stream=False
            )
            assert result == "This is a test response. [doc_1] [doc_2]"

    @pytest.mark.asyncio
    async def test_generate_with_streaming(self, provider, mock_httpx_response):
        """Test generation with streaming."""
        mock_httpx_response.aiter_text.return_value = async_iter(["This is a test ", "response. [doc_1] ", "[doc_2]"])

        with patch.object(provider._http_client, '_request_with_retry', AsyncMock(
            return_value=mock_httpx_response
        )):
            result = await provider.generate(
                prompt="Test prompt",
                temperature=0.2,
                max_tokens=512,
                timeout_s=60.0,
                stream=True
            )
            assert result == "This is a test response. [doc_1] [doc_2]"

    @pytest.mark.asyncio
    async def test_generate_timeout(self, provider):
        """Test generation timeout handling."""
        with patch.object(provider._http_client, '_request_with_retry', AsyncMock(
            side_effect=GenerationTimeoutError("Request timed out after 60.0s")
        )):
            with pytest.raises(GenerationTimeoutError):
                await provider.generate(
                    prompt="Test prompt",
                    temperature=0.2,
                    max_tokens=512,
                    timeout_s=60.0,
                    stream=False
                )

    @pytest.mark.asyncio
    async def test_generate_provider_unavailable(self, provider):
        """Test generation when provider is unavailable."""
        with patch.object(provider._http_client, '_request_with_retry', AsyncMock(
            side_effect=LLMProviderUnavailableError("Provider failed")
        )):
            with pytest.raises(LLMProviderUnavailableError):
                await provider.generate(
                    prompt="Test prompt",
                    temperature=0.2,
                    max_tokens=512,
                    timeout_s=60.0,
                    stream=False
                )

    @pytest.mark.asyncio
    async def test_generate_http_error(self, provider):
        """Test generation with HTTP error."""
        with patch.object(provider._http_client, '_request_with_retry', AsyncMock(
            side_effect=LLMProviderUnavailableError("HTTP 500: Internal Server Error")
        )):
            with pytest.raises(LLMProviderUnavailableError):
                await provider.generate(
                    prompt="Test prompt",
                    temperature=0.2,
                    max_tokens=512,
                    timeout_s=60.0,
                    stream=False
                )

    def test_extract_token_usage(self, provider, mock_httpx_response):
        """Test token usage extraction."""
        usage = provider.extract_token_usage(mock_httpx_response)
        assert usage == {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

    def test_extract_token_usage_invalid_response(self, provider):
        """Test token usage extraction with invalid response."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.json.side_effect = ValueError("Invalid JSON")

        usage = provider.extract_token_usage(mock_response)
        assert usage is None

    def test_settings_default_values(self):
        """Test that default settings are correctly set."""
        settings = OpenAICompatibleSettings()
        assert settings.base_url == "http://localhost:8000/v1"
        assert settings.model == "gpt-3.5-turbo"
        assert settings.max_retries == 3
        assert settings.temperature == 0.2

    def test_settings_custom_values(self):
        """Test that custom settings are correctly set."""
        settings = OpenAICompatibleSettings(
            base_url="https://api.openai.com/v1",
            model="gpt-4",
            api_key="test-key",
            max_retries=5,
            timeout_s=120.0
        )
        assert settings.base_url == "https://api.openai.com/v1"
        assert settings.model == "gpt-4"
        assert settings.api_key == "test-key"
        assert settings.max_retries == 5
        assert settings.timeout_s == 120.0


class TestHTTPProviderClient:
    """Test suite for HTTPProviderClient."""

    @pytest.fixture
    def http_client(self):
        """Create a test HTTP client instance."""
        return HTTPProviderClient(
            base_url="http://localhost:8000",
            model="test-model",
            timeout_s=30.0
        )

    @pytest.mark.asyncio
    async def test_request_with_retry_success(self, http_client):
        """Test successful request with retry logic."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        with patch(
            'backend.generation.providers.common.http_client.get_provider_client',
            AsyncMock(return_value=mock_client),
        ):
            result = await http_client._request_with_retry("GET", "test")
            assert result == mock_response

    @pytest.mark.asyncio
    async def test_request_with_retry_timeout(self, http_client):
        """Test request timeout with retry logic."""
        mock_client = AsyncMock()
        mock_client.request.side_effect = httpx.TimeoutException("Timeout")

        with patch(
            'backend.generation.providers.common.http_client.get_provider_client',
            AsyncMock(return_value=mock_client),
        ):
            with pytest.raises(GenerationTimeoutError):
                await http_client._request_with_retry("GET", "test")

    @pytest.mark.asyncio
    async def test_request_with_retry_max_retries_exceeded(self, http_client):
        """Test request when max retries are exceeded."""
        mock_client = AsyncMock()
        mock_client.request.side_effect = Exception("Some error")

        with patch(
            'backend.generation.providers.common.http_client.get_provider_client',
            AsyncMock(return_value=mock_client),
        ):
            with pytest.raises(LLMProviderUnavailableError):
                await http_client._request_with_retry("GET", "test")

    @pytest.mark.asyncio
    async def test_health_check(self, http_client):
        """Test health check functionality."""
        with patch.object(http_client, '_request_with_retry', AsyncMock(
            return_value=MagicMock(spec=httpx.Response, status_code=200, json=AsyncMock(return_value={}))
        )):
            result = await http_client.health_check()
            assert result["status"] == "healthy"
            assert result["status_code"] == 200

    def test_build_headers(self, http_client):
        """Test header building."""
        headers = http_client._build_headers({"X-Custom": "value"})
        assert headers["Content-Type"] == "application/json"
        assert headers["X-Custom"] == "value"

    def test_build_headers_without_additional(self, http_client):
        """Test header building without additional headers."""
        headers = http_client._build_headers()
        assert headers == {"Content-Type": "application/json"}


def test_provider_interface_implementation():
    """Test that all providers implement the LLMProvider interface."""
    from backend.generation.providers.openai_provider import OpenAICompatibleProvider

    provider = OpenAICompatibleProvider(model="test")

    assert isinstance(provider, LLMProvider)
    assert hasattr(provider, 'provider_name')
    assert hasattr(provider, 'model_name')
    assert hasattr(provider, 'generate')
    assert hasattr(provider, 'health_check')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
