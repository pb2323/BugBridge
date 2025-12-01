"""
XAI (xAI) API Integration for LangChain

Custom LangChain-compatible wrapper for XAI's Grok API to support
deterministic agent behavior with structured outputs.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Type, cast

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import BaseModel, Field

from bugbridge.config import get_settings
from bugbridge.utils.logging import get_logger
from bugbridge.utils.retry import async_retry_with_backoff

logger = get_logger(__name__)


class XAIAPIError(Exception):
    """Raised when XAI API returns an error."""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict[str, Any]] = None):
        """Initialize XAI API error with message, status code, and response."""
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ChatXAI(BaseChatModel):
    """
    LangChain-compatible chat model for XAI's Grok API.

    This class provides a seamless integration with LangChain's chat model
    interface, supporting structured outputs and deterministic behavior.
    """

    api_key: str = Field(..., description="XAI API key")
    model: str = Field("grok-4-fast-reasoning", description="Grok model to use (grok-beta, grok-2, or grok-4-fast-reasoning)")
    temperature: float = Field(0.0, description="Temperature for deterministic outputs (0.0 recommended)")
    max_tokens: int = Field(2048, description="Maximum tokens in response")
    base_url: str = Field("https://api.x.ai/v1", description="XAI API base URL")
    timeout: int = Field(60, description="Request timeout in seconds")

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True

    @property
    def _llm_type(self) -> str:
        """Return identifier of LLM type."""
        return "xai-grok"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        Synchronous generation (not recommended, use async).

        Note: This is required by BaseChatModel but async is preferred.
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs))

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        Async generation using XAI API.

        Args:
            messages: List of chat messages.
            stop: Optional stop sequences.
            run_manager: Optional callback manager.
            **kwargs: Additional parameters.

        Returns:
            ChatResult with generated message.
        """
        # Convert LangChain messages to XAI format
        xai_messages = self._convert_messages_to_xai_format(messages)

        # Prepare request payload
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": xai_messages,
            "temperature": self.temperature,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }

        # Add stop sequences if provided
        if stop:
            payload["stop"] = stop

        # Make API request
        try:
            response = await self._make_request("/chat/completions", payload)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"XAI API generation error: {str(e)}", exc_info=True)
            raise

    def _convert_messages_to_xai_format(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """
        Convert LangChain messages to XAI API format.

        Args:
            messages: List of LangChain messages.

        Returns:
            List of XAI-formatted messages.
        """
        xai_messages = []

        for message in messages:
            if isinstance(message, SystemMessage):
                xai_messages.append({"role": "system", "content": message.content})
            elif isinstance(message, HumanMessage):
                xai_messages.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                xai_messages.append({"role": "assistant", "content": message.content})
            else:
                # For other message types, try to extract content
                content = getattr(message, "content", str(message))
                xai_messages.append({"role": "user", "content": content})

        return xai_messages

    @async_retry_with_backoff(
        exceptions=(httpx.HTTPError, httpx.RequestError, XAIAPIError),
        max_retries=3,
        base_delay=2.0,
    )
    async def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make async HTTP request to XAI API.

        Args:
            endpoint: API endpoint path.
            payload: Request payload.

        Returns:
            JSON response from API.

        Raises:
            XAIAPIError: If API returns an error.
        """
        url = f"{self.base_url}{endpoint}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.debug(
                    f"Making request to XAI API: {endpoint}",
                    extra={"model": self.model, "endpoint": endpoint},
                )

                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                result = response.json()

                # Check for API-level errors
                if "error" in result:
                    error_data = result["error"]
                    error_msg = error_data.get("message", "Unknown XAI API error")
                    raise XAIAPIError(
                        f"XAI API error: {error_msg}",
                        status_code=response.status_code,
                        response=result,
                    )

                return result

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error {e.response.status_code} for {endpoint}: {e.response.text}",
                extra={"endpoint": endpoint, "status_code": e.response.status_code},
            )
            raise XAIAPIError(
                f"HTTP {e.response.status_code}: {e.response.text}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            logger.error(f"Request error for {endpoint}: {str(e)}", extra={"endpoint": endpoint})
            raise XAIAPIError(f"Request failed: {str(e)}") from e

    def _parse_response(self, response: Dict[str, Any]) -> ChatResult:
        """
        Parse XAI API response into LangChain ChatResult.

        Args:
            response: XAI API response dictionary.

        Returns:
            ChatResult with generated message.
        """
        choices = response.get("choices", [])
        if not choices:
            raise XAIAPIError("No choices in XAI API response", response=response)

        choice = choices[0]
        message_data = choice.get("message", {})
        content = message_data.get("content", "")

        # Create AIMessage from response
        ai_message = AIMessage(content=content)

        # Create generation
        generation = ChatGeneration(message=ai_message)

        # Extract usage information if available
        usage = response.get("usage", {})
        generation.generation_info = {
            "finish_reason": choice.get("finish_reason"),
            "usage": usage,
        }

        return ChatResult(generations=[generation])

    async def astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        """
        Stream responses from XAI API.

        Args:
            messages: List of chat messages.
            stop: Optional stop sequences.
            run_manager: Optional callback manager.
            **kwargs: Additional parameters.

        Yields:
            ChatGenerationChunk for each token/segment.
        """
        # For now, implement non-streaming and yield final result
        # Full streaming support can be added later if needed
        result = await self._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)

        if result.generations:
            generation = result.generations[0]
            # Yield the entire message as a chunk
            chunk = ChatGenerationChunk(
                message=AIMessageChunk(content=generation.message.content),
                generation_info=generation.generation_info,
            )
            yield chunk

    def with_structured_output(
        self,
        schema: Type[BaseModel],
        **kwargs: Any,
    ) -> Any:
        """
        Return a Runnable that uses structured output.

        This method enables structured output parsing with Pydantic models.

        Args:
            schema: Pydantic model class for structured output.
            **kwargs: Additional parameters for structured output.

        Returns:
            Runnable that returns structured output.
        """
        from langchain_core.output_parsers import PydanticOutputParser

        parser = PydanticOutputParser(pydantic_object=schema)

        # Create a chain that parses the output
        from langchain_core.runnables import RunnableLambda

        async def parse_output(messages: List[BaseMessage]) -> BaseModel:
            """Parse LLM output into Pydantic model."""
            result = await self._agenerate(messages, **kwargs)

            if not result.generations or not result.generations[0].message.content:
                raise ValueError("Empty response from XAI API")

            content = result.generations[0].message.content

            # Try to parse as JSON first
            try:
                # Extract JSON from markdown code blocks if present
                if "```json" in content:
                    start = content.find("```json") + 7
                    end = content.find("```", start)
                    content = content[start:end].strip()
                elif "```" in content:
                    start = content.find("```") + 3
                    end = content.find("```", start)
                    content = content[start:end].strip()

                parsed_json = json.loads(content)
                return schema(**parsed_json)

            except (json.JSONDecodeError, ValueError) as e:
                # If JSON parsing fails, use PydanticOutputParser
                logger.warning(f"Failed to parse JSON directly, using parser: {str(e)}")
                parsed = parser.parse(content)
                return parsed

        return RunnableLambda(parse_output)


def get_xai_llm(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> ChatXAI:
    """
    Create a configured ChatXAI instance with settings from config.

    Args:
        api_key: XAI API key (defaults to config).
        model: Model name (defaults to config).
        temperature: Temperature (defaults to config).
        max_tokens: Max tokens (defaults to config).

    Returns:
        Configured ChatXAI instance.
    """
    try:
        settings = get_settings()
        return ChatXAI(
            api_key=api_key or settings.xai.api_key.get_secret_value(),
            model=model or settings.xai.model,
            temperature=temperature if temperature is not None else settings.xai.temperature,
            max_tokens=max_tokens or settings.xai.max_output_tokens,
        )
    except Exception:
        # Config not available, require explicit parameters
        if not api_key:
            raise ValueError("API key must be provided if config is not available")
        return ChatXAI(
            api_key=api_key,
            model=model or "grok-4-fast-reasoning",
            temperature=temperature if temperature is not None else 0.0,
            max_tokens=max_tokens or 2048,
        )


__all__ = [
    "ChatXAI",
    "XAIAPIError",
    "get_xai_llm",
]

