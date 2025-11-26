"""Base AI Provider and Factory.

This module provides the base class for AI providers and a factory
for creating provider instances.
"""

import os
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional


class ProviderType(Enum):
    """Supported AI provider types."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    XAI = "xai"
    GEMINI = "gemini"
    OLLAMA = "ollama"


@dataclass
class ModelConfig:
    """Configuration for an AI model."""

    provider: ProviderType
    model_name: str
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    timeout: int = 120
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """A chat message."""

    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class CompletionResponse:
    """Response from a completion request."""

    content: str
    model: str
    provider: ProviderType
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: Optional[str] = None
    raw_response: Optional[Any] = None


class AIProvider(ABC):
    """Abstract base class for AI providers.

    All provider implementations should extend this class and implement
    the required methods for chat completion and streaming.
    """

    def __init__(self, config: ModelConfig) -> None:
        """Initialize the AI provider.

        Args:
            config: Model configuration
        """
        self.config = config
        self._client: Optional[Any] = None

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Get the provider type."""
        pass

    @abstractmethod
    def _create_client(self) -> Any:
        """Create the provider-specific client."""
        pass

    @abstractmethod
    def complete(self, messages: List[Message], **kwargs: Any) -> CompletionResponse:
        """Send a completion request.

        Args:
            messages: List of chat messages
            **kwargs: Additional provider-specific parameters

        Returns:
            Completion response
        """
        pass

    @abstractmethod
    def complete_stream(self, messages: List[Message], **kwargs: Any) -> Any:
        """Send a streaming completion request.

        Args:
            messages: List of chat messages
            **kwargs: Additional provider-specific parameters

        Yields:
            Completion chunks
        """
        pass

    def get_client(self) -> Any:
        """Get or create the provider client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client


class OpenAIProvider(AIProvider):
    """OpenAI API provider."""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENAI

    def _create_client(self) -> Any:
        try:
            from openai import OpenAI

            api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
            base_url = self.config.base_url or os.getenv("OPENAI_BASE_URL")

            return OpenAI(api_key=api_key, base_url=base_url, timeout=self.config.timeout)
        except ImportError:
            raise ImportError("openai package is required for OpenAI provider")

    def complete(self, messages: List[Message], **kwargs: Any) -> CompletionResponse:
        client = self.get_client()

        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]

        response = client.chat.completions.create(
            model=self.config.model_name,
            messages=formatted_messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            **self.config.extra_params,
        )

        return CompletionResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            provider=self.provider_type,
            usage={"prompt_tokens": response.usage.prompt_tokens if response.usage else 0, "completion_tokens": response.usage.completion_tokens if response.usage else 0},
            finish_reason=response.choices[0].finish_reason,
            raw_response=response,
        )

    def complete_stream(self, messages: List[Message], **kwargs: Any) -> Any:
        client = self.get_client()

        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]

        stream = client.chat.completions.create(
            model=self.config.model_name,
            messages=formatted_messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            stream=True,
            **self.config.extra_params,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider."""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.ANTHROPIC

    def _create_client(self) -> Any:
        try:
            from anthropic import Anthropic

            api_key = self.config.api_key or os.getenv("ANTHROPIC_API_KEY")

            return Anthropic(api_key=api_key, timeout=self.config.timeout)
        except ImportError:
            raise ImportError("anthropic package is required for Anthropic provider")

    def complete(self, messages: List[Message], **kwargs: Any) -> CompletionResponse:
        client = self.get_client()

        # Separate system message
        system_message = ""
        chat_messages = []

        for m in messages:
            if m.role == "system":
                system_message = m.content
            else:
                chat_messages.append({"role": m.role, "content": m.content})

        response = client.messages.create(
            model=self.config.model_name,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            system=system_message if system_message else None,
            messages=chat_messages,
            **self.config.extra_params,
        )

        return CompletionResponse(
            content=response.content[0].text if response.content else "",
            model=response.model,
            provider=self.provider_type,
            usage={"prompt_tokens": response.usage.input_tokens, "completion_tokens": response.usage.output_tokens},
            finish_reason=response.stop_reason,
            raw_response=response,
        )

    def complete_stream(self, messages: List[Message], **kwargs: Any) -> Any:
        client = self.get_client()

        system_message = ""
        chat_messages = []

        for m in messages:
            if m.role == "system":
                system_message = m.content
            else:
                chat_messages.append({"role": m.role, "content": m.content})

        with client.messages.stream(
            model=self.config.model_name,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            system=system_message if system_message else None,
            messages=chat_messages,
            **self.config.extra_params,
        ) as stream:
            for text in stream.text_stream:
                yield text


class GroqProvider(AIProvider):
    """Groq API provider for ultra-fast inference."""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.GROQ

    def _create_client(self) -> Any:
        try:
            from groq import Groq

            api_key = self.config.api_key or os.getenv("GROQ_API_KEY")

            return Groq(api_key=api_key, timeout=self.config.timeout)
        except ImportError:
            raise ImportError("groq package is required for Groq provider")

    def complete(self, messages: List[Message], **kwargs: Any) -> CompletionResponse:
        client = self.get_client()

        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]

        response = client.chat.completions.create(
            model=self.config.model_name,
            messages=formatted_messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            **self.config.extra_params,
        )

        return CompletionResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            provider=self.provider_type,
            usage={"prompt_tokens": response.usage.prompt_tokens if response.usage else 0, "completion_tokens": response.usage.completion_tokens if response.usage else 0},
            finish_reason=response.choices[0].finish_reason,
            raw_response=response,
        )

    def complete_stream(self, messages: List[Message], **kwargs: Any) -> Any:
        client = self.get_client()

        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]

        stream = client.chat.completions.create(
            model=self.config.model_name,
            messages=formatted_messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            stream=True,
            **self.config.extra_params,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class GeminiProvider(AIProvider):
    """Google Gemini API provider."""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.GEMINI

    def _create_client(self) -> Any:
        try:
            import google.generativeai as genai

            api_key = self.config.api_key or os.getenv("GOOGLE_GEMINI_API_KEY")
            genai.configure(api_key=api_key)

            return genai.GenerativeModel(self.config.model_name)
        except ImportError:
            raise ImportError("google-generativeai package is required for Gemini provider")

    def complete(self, messages: List[Message], **kwargs: Any) -> CompletionResponse:
        client = self.get_client()

        # Convert messages to Gemini format
        prompt_parts = []
        for m in messages:
            if m.role == "system":
                prompt_parts.append(f"System: {m.content}")
            elif m.role == "user":
                prompt_parts.append(f"User: {m.content}")
            elif m.role == "assistant":
                prompt_parts.append(f"Assistant: {m.content}")

        prompt = "\n\n".join(prompt_parts)

        generation_config = {"max_output_tokens": kwargs.get("max_tokens", self.config.max_tokens), "temperature": kwargs.get("temperature", self.config.temperature)}

        response = client.generate_content(prompt, generation_config=generation_config)

        return CompletionResponse(content=response.text if response.text else "", model=self.config.model_name, provider=self.provider_type, usage={}, raw_response=response)

    def complete_stream(self, messages: List[Message], **kwargs: Any) -> Any:
        client = self.get_client()

        prompt_parts = []
        for m in messages:
            if m.role == "system":
                prompt_parts.append(f"System: {m.content}")
            elif m.role == "user":
                prompt_parts.append(f"User: {m.content}")
            elif m.role == "assistant":
                prompt_parts.append(f"Assistant: {m.content}")

        prompt = "\n\n".join(prompt_parts)

        generation_config = {"max_output_tokens": kwargs.get("max_tokens", self.config.max_tokens), "temperature": kwargs.get("temperature", self.config.temperature)}

        response = client.generate_content(prompt, generation_config=generation_config, stream=True)

        for chunk in response:
            if chunk.text:
                yield chunk.text


class OllamaProvider(AIProvider):
    """Ollama local inference provider."""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OLLAMA

    def _create_client(self) -> Any:
        try:
            import httpx

            base_url = self.config.base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")

            return httpx.Client(base_url=base_url, timeout=self.config.timeout)
        except ImportError:
            raise ImportError("httpx package is required for Ollama provider")

    def complete(self, messages: List[Message], **kwargs: Any) -> CompletionResponse:
        client = self.get_client()

        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]

        response = client.post(
            "/api/chat",
            json={"model": self.config.model_name, "messages": formatted_messages, "stream": False, "options": {"temperature": kwargs.get("temperature", self.config.temperature)}},
        )
        response.raise_for_status()
        data = response.json()

        return CompletionResponse(content=data.get("message", {}).get("content", ""), model=self.config.model_name, provider=self.provider_type, usage={}, raw_response=data)

    def complete_stream(self, messages: List[Message], **kwargs: Any) -> Any:
        import httpx

        base_url = self.config.base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")

        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]

        with httpx.stream(
            "POST",
            f"{base_url}/api/chat",
            json={"model": self.config.model_name, "messages": formatted_messages, "stream": True, "options": {"temperature": kwargs.get("temperature", self.config.temperature)}},
            timeout=self.config.timeout,
        ) as response:
            import json

            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if data.get("message", {}).get("content"):
                        yield data["message"]["content"]


class XAIProvider(AIProvider):
    """xAI Grok API provider."""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.XAI

    def _create_client(self) -> Any:
        try:
            from openai import OpenAI

            api_key = self.config.api_key or os.getenv("XAI_API_KEY")
            base_url = self.config.base_url or "https://api.x.ai/v1"

            return OpenAI(api_key=api_key, base_url=base_url, timeout=self.config.timeout)
        except ImportError:
            raise ImportError("openai package is required for xAI provider")

    def complete(self, messages: List[Message], **kwargs: Any) -> CompletionResponse:
        client = self.get_client()

        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]

        response = client.chat.completions.create(
            model=self.config.model_name,
            messages=formatted_messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            **self.config.extra_params,
        )

        return CompletionResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            provider=self.provider_type,
            usage={"prompt_tokens": response.usage.prompt_tokens if response.usage else 0, "completion_tokens": response.usage.completion_tokens if response.usage else 0},
            finish_reason=response.choices[0].finish_reason,
            raw_response=response,
        )

    def complete_stream(self, messages: List[Message], **kwargs: Any) -> Any:
        client = self.get_client()

        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]

        stream = client.chat.completions.create(
            model=self.config.model_name,
            messages=formatted_messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            stream=True,
            **self.config.extra_params,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AIProviderFactory:
    """Factory for creating AI provider instances."""

    # Default models for each provider
    DEFAULT_MODELS = {
        ProviderType.OPENAI: "gpt-4.1",
        ProviderType.ANTHROPIC: "claude-sonnet-4-5",
        ProviderType.GROQ: "llama-3.3-70b-versatile",
        ProviderType.XAI: "grok-2-latest",
        ProviderType.GEMINI: "gemini-2.0-flash",
        ProviderType.OLLAMA: "llama3.2",
    }

    # Provider class mapping
    PROVIDERS = {
        ProviderType.OPENAI: OpenAIProvider,
        ProviderType.ANTHROPIC: AnthropicProvider,
        ProviderType.GROQ: GroqProvider,
        ProviderType.XAI: XAIProvider,
        ProviderType.GEMINI: GeminiProvider,
        ProviderType.OLLAMA: OllamaProvider,
    }

    @classmethod
    def create(
        cls,
        provider_type: ProviderType,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs: Any,
    ) -> AIProvider:
        """Create an AI provider instance.

        Args:
            provider_type: Type of provider
            model_name: Model name (uses default if not provided)
            api_key: API key (uses environment variable if not provided)
            **kwargs: Additional configuration

        Returns:
            Configured AI provider instance
        """
        if provider_type not in cls.PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider_type}")

        model = model_name or cls.DEFAULT_MODELS.get(provider_type, "")

        config = ModelConfig(
            provider=provider_type,
            model_name=model,
            api_key=api_key,
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
            timeout=kwargs.get("timeout", 120),
            base_url=kwargs.get("base_url"),
            extra_params=kwargs.get("extra_params", {}),
        )

        provider_class = cls.PROVIDERS[provider_type]
        return provider_class(config)

    @classmethod
    def create_from_string(cls, provider_str: str, model_name: Optional[str] = None, **kwargs: Any) -> AIProvider:
        """Create provider from string name.

        Args:
            provider_str: Provider name string
            model_name: Optional model name
            **kwargs: Additional configuration

        Returns:
            Configured AI provider instance
        """
        try:
            provider_type = ProviderType(provider_str.lower())
        except ValueError:
            raise ValueError(f"Unknown provider: {provider_str}")

        return cls.create(provider_type, model_name, **kwargs)

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available provider names."""
        return [p.value for p in ProviderType]

    @classmethod
    def get_default_model(cls, provider_type: ProviderType) -> str:
        """Get default model for a provider."""
        return cls.DEFAULT_MODELS.get(provider_type, "")
