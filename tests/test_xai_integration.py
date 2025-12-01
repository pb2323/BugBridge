"""
Tests for XAI (xAI) API Integration.
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from bugbridge.integrations.xai import ChatXAI, XAIAPIError, get_xai_llm


class SampleOutput(BaseModel):
    """Sample Pydantic model for structured output testing."""

    result: str = Field(..., description="Test result")
    score: int = Field(..., description="Test score")


@pytest.mark.asyncio
async def test_chatxai_initialization():
    """ChatXAI should initialize with correct parameters."""
    llm = ChatXAI(
        api_key="test_key",
        model="grok-4-fast-reasoning",
        temperature=0.0,
        max_tokens=2048,
    )

    assert llm.api_key == "test_key"
    assert llm.model == "grok-4-fast-reasoning"
    assert llm.temperature == 0.0
    assert llm.max_tokens == 2048
    assert llm._llm_type == "xai-grok"


@pytest.mark.asyncio
async def test_chatxai_defaults():
    """ChatXAI should use default values when not specified."""
    llm = ChatXAI(api_key="test_key")

    assert llm.model == "grok-4-fast-reasoning"
    assert llm.temperature == 0.0
    assert llm.max_tokens == 2048
    assert llm.base_url == "https://api.x.ai/v1"


@pytest.mark.asyncio
async def test_convert_messages_to_xai_format():
    """ChatXAI should convert LangChain messages to XAI format."""
    llm = ChatXAI(api_key="test_key")

    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="Hello!"),
        AIMessage(content="Hi there!"),
    ]

    xai_messages = llm._convert_messages_to_xai_format(messages)

    assert len(xai_messages) == 3
    assert xai_messages[0] == {"role": "system", "content": "You are a helpful assistant."}
    assert xai_messages[1] == {"role": "user", "content": "Hello!"}
    assert xai_messages[2] == {"role": "assistant", "content": "Hi there!"}


@pytest.mark.asyncio
async def test_parse_response_success():
    """ChatXAI should parse successful API response."""
    llm = ChatXAI(api_key="test_key")

    response: Dict[str, Any] = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Test response",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }

    result = llm._parse_response(response)

    assert result.generations[0].message.content == "Test response"
    assert result.generations[0].generation_info["finish_reason"] == "stop"
    assert "usage" in result.generations[0].generation_info
    # llm_output is not set in the current implementation


@pytest.mark.asyncio
async def test_parse_response_empty_choices():
    """ChatXAI should raise error for empty choices."""
    llm = ChatXAI(api_key="test_key")

    response: Dict[str, Any] = {"choices": []}

    with pytest.raises(XAIAPIError, match="No choices"):
        llm._parse_response(response)


@pytest.mark.asyncio
async def test_make_request_success(monkeypatch):
    """ChatXAI should make successful API request."""
    llm = ChatXAI(api_key="test_key")

    async def mock_post(*args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Test"},
                    "finish_reason": "stop",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        return mock_response

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post_func:
        mock_post_func.return_value = await mock_post()

        response = await llm._make_request("/chat/completions", {"model": "grok-4-fast-reasoning"})

        assert "choices" in response
        mock_post_func.assert_called_once()


@pytest.mark.asyncio
async def test_make_request_api_error(monkeypatch):
    """ChatXAI should raise XAIAPIError on API error (with retry logic)."""
    from bugbridge.utils.retry import RetryError

    llm = ChatXAI(api_key="test_key")

    async def mock_post(*args, **kwargs):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.return_value = {"error": {"message": "Unauthorized"}}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )
        return mock_response

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post_func:
        mock_post_func.return_value = await mock_post()

        # Retry logic will exhaust all attempts, so expect RetryError or XAIAPIError
        with pytest.raises((XAIAPIError, RetryError)):
            await llm._make_request("/chat/completions", {"model": "grok-4-fast-reasoning"})


@pytest.mark.asyncio
async def test_agenerate_success(monkeypatch):
    """ChatXAI._agenerate should generate responses successfully."""
    llm = ChatXAI(api_key="test_key", model="grok-4-fast-reasoning")

    async def mock_make_request(endpoint, payload):
        return {
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Generated response"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        }

    monkeypatch.setattr(llm, "_make_request", mock_make_request)

    messages = [HumanMessage(content="Test prompt")]
    result = await llm._agenerate(messages)

    assert result.generations[0].message.content == "Generated response"
    # llm_output is not set in the current implementation


@pytest.mark.asyncio
async def test_with_structured_output_json(monkeypatch):
    """ChatXAI.with_structured_output should parse JSON response."""
    llm = ChatXAI(api_key="test_key")

    async def mock_agenerate(messages, **kwargs):
        return type(
            "ChatResult",
            (),
            {
                "generations": [
                    type(
                        "Generation",
                        (),
                        {
                            "message": type("Message", (), {"content": '{"result": "success", "score": 100}'}),
                        },
                    )
                ],
            },
        )()

    monkeypatch.setattr(llm, "_agenerate", mock_agenerate)

    structured_llm = llm.with_structured_output(SampleOutput)
    messages = [HumanMessage(content="Test")]
    result = await structured_llm.ainvoke(messages)

    assert isinstance(result, SampleOutput)
    assert result.result == "success"
    assert result.score == 100


@pytest.mark.asyncio
async def test_with_structured_output_markdown_json(monkeypatch):
    """ChatXAI.with_structured_output should extract JSON from markdown code blocks."""
    llm = ChatXAI(api_key="test_key")

    async def mock_agenerate(messages, **kwargs):
        return type(
            "ChatResult",
            (),
            {
                "generations": [
                    type(
                        "Generation",
                        (),
                        {
                            "message": type(
                                "Message",
                                (),
                                {"content": '```json\n{"result": "parsed", "score": 42}\n```'},
                            ),
                        },
                    )
                ],
            },
        )()

    monkeypatch.setattr(llm, "_agenerate", mock_agenerate)

    structured_llm = llm.with_structured_output(SampleOutput)
    messages = [HumanMessage(content="Test")]
    result = await structured_llm.ainvoke(messages)

    assert isinstance(result, SampleOutput)
    assert result.result == "parsed"
    assert result.score == 42


@pytest.mark.asyncio
async def test_astream_success(monkeypatch):
    """ChatXAI.astream should stream responses (currently yields single chunk from _agenerate)."""
    llm = ChatXAI(api_key="test_key")

    async def mock_agenerate(messages, **kwargs):
        from langchain_core.outputs import ChatGeneration, ChatResult
        from langchain_core.messages import AIMessage

        generation = ChatGeneration(
            message=AIMessage(content="Hello world"),
            generation_info={"finish_reason": "stop"},
        )
        return ChatResult(generations=[generation])

    monkeypatch.setattr(llm, "_agenerate", mock_agenerate)

    messages = [HumanMessage(content="Test")]
    chunks = []
    async for chunk in llm.astream(messages):
        chunks.append(chunk)

    # Current implementation yields single chunk from _agenerate result
    assert len(chunks) == 1
    assert chunks[0].message.content == "Hello world"


@pytest.mark.asyncio
async def test_get_xai_llm_with_explicit_params():
    """get_xai_llm should create LLM with explicit parameters."""
    llm = get_xai_llm(
        api_key="explicit_key",
        model="grok-2",
        temperature=0.5,
        max_tokens=1024,
    )

    assert llm.api_key == "explicit_key"
    assert llm.model == "grok-2"
    assert llm.temperature == 0.5
    assert llm.max_tokens == 1024


@pytest.mark.asyncio
async def test_get_xai_llm_with_config(monkeypatch):
    """get_xai_llm should use config settings when available."""
    from bugbridge.config import XAISettings

    mock_settings = MagicMock()
    mock_settings.xai = XAISettings(
        api_key="config_key",
        model="grok-4-fast-reasoning",
        temperature=0.0,
        max_output_tokens=2048,
    )

    with patch("bugbridge.integrations.xai.get_settings", return_value=mock_settings):
        llm = get_xai_llm()

        assert llm.api_key == "config_key"
        assert llm.model == "grok-4-fast-reasoning"
        assert llm.temperature == 0.0
        assert llm.max_tokens == 2048


@pytest.mark.asyncio
async def test_get_xai_llm_fallback_without_config():
    """get_xai_llm should use fallback defaults when config unavailable."""
    with patch("bugbridge.integrations.xai.get_settings", side_effect=Exception("Config unavailable")):
        llm = get_xai_llm(api_key="fallback_key")

        assert llm.api_key == "fallback_key"
        assert llm.model == "grok-4-fast-reasoning"  # Default fallback
        assert llm.temperature == 0.0


@pytest.mark.asyncio
async def test_get_xai_llm_requires_api_key_without_config():
    """get_xai_llm should raise error if API key not provided and config unavailable."""
    with patch("bugbridge.integrations.xai.get_settings", side_effect=Exception("Config unavailable")):
        with pytest.raises(ValueError, match="API key must be provided"):
            get_xai_llm()


@pytest.mark.asyncio
async def test_xai_api_error_initialization():
    """XAIAPIError should store status code and response."""
    error = XAIAPIError("Test error", status_code=500, response={"error": "Internal Server Error"})

    assert str(error) == "Test error"
    assert error.status_code == 500
    assert error.response == {"error": "Internal Server Error"}

