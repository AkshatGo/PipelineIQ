"""LLM Gateway: unified interface for multiple LLM providers with fallback."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog
from openai import AsyncOpenAI

from pipelineiq.config import Settings

logger = structlog.get_logger()


class Provider(str, Enum):
    """Supported LLM providers."""

    GITHUB_MODELS = "github_models"
    GROQ = "groq"
    OPENAI = "openai"


class AgentType(str, Enum):
    """Pipeline agents that use LLMs."""

    MONITOR = "monitor"
    DIAGNOSIS = "diagnosis"
    RISK = "risk"
    AUTOFIX = "autofix"


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    provider: Provider
    model: str
    usage: dict[str, int] | None = None
    latency_ms: int = 0


@dataclass
class LLMRequest:
    """Request to an LLM provider."""

    messages: list[dict[str, str]]
    model: str
    temperature: float = 0.1
    max_tokens: int | None = None
    response_format: dict[str, Any] | None = None


class LLMProviderError(Exception):
    """Error from an LLM provider."""

    def __init__(self, provider: Provider, message: str, original: Exception | None = None):
        self.provider = provider
        self.original = original
        super().__init__(f"{provider.value}: {message}")


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Generate a completion."""

    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model for this provider."""


class GitHubModelsProvider(BaseLLMProvider):
    """GitHub Models API provider."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.client = AsyncOpenAI(
            api_key=settings.GITHUB_TOKEN,
            base_url=settings.GITHUB_MODELS_API_BASE_URL,
        )

    async def complete(self, request: LLMRequest) -> LLMResponse:
        start = time.perf_counter()
        try:
            response = await self.client.chat.completions.create(  # type: ignore[call-overload]
                model=request.model,
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                response_format=request.response_format,
            )
            latency = int((time.perf_counter() - start) * 1000)
            return LLMResponse(
                content=response.choices[0].message.content or "",
                provider=Provider.GITHUB_MODELS,
                model=request.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                latency_ms=latency,
            )
        except Exception as exc:
            raise LLMProviderError(Provider.GITHUB_MODELS, str(exc), exc) from exc

    def get_default_model(self) -> str:
        return "gpt-4o-mini"


class GroqProvider(BaseLLMProvider):
    """Groq API provider."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_API_BASE_URL,
        )

    async def complete(self, request: LLMRequest) -> LLMResponse:
        start = time.perf_counter()
        try:
            response = await self.client.chat.completions.create(  # type: ignore[call-overload]
                model=request.model,
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                response_format=request.response_format,
            )
            latency = int((time.perf_counter() - start) * 1000)
            return LLMResponse(
                content=response.choices[0].message.content or "",
                provider=Provider.GROQ,
                model=request.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                latency_ms=latency,
            )
        except Exception as exc:
            raise LLMProviderError(Provider.GROQ, str(exc), exc) from exc

    def get_default_model(self) -> str:
        return "llama-3.3-70b-versatile"


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE_URL,
        )

    async def complete(self, request: LLMRequest) -> LLMResponse:
        start = time.perf_counter()
        try:
            response = await self.client.chat.completions.create(  # type: ignore[call-overload]
                model=request.model,
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                response_format=request.response_format,
            )
            latency = int((time.perf_counter() - start) * 1000)
            return LLMResponse(
                content=response.choices[0].message.content or "",
                provider=Provider.OPENAI,
                model=request.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                latency_ms=latency,
            )
        except Exception as exc:
            raise LLMProviderError(Provider.OPENAI, str(exc), exc) from exc

    def get_default_model(self) -> str:
        return "gpt-4o-mini"


class CircuitBreaker:
    """Circuit breaker for LLM providers."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time: float | None = None
        self.state = "closed"  # closed, open, half-open

    def record_success(self) -> None:
        self.failures = 0
        self.state = "closed"

    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "open"

    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if (
                self.last_failure_time
                and time.time() - self.last_failure_time > self.recovery_timeout
            ):
                self.state = "half-open"
                return True
            return False
        # half-open
        return True


class LLMCircuitBreakers:
    """Manages circuit breakers for all providers."""

    def __init__(self) -> None:
        self._breakers: dict[Provider, CircuitBreaker] = {
            Provider.GITHUB_MODELS: CircuitBreaker(),
            Provider.GROQ: CircuitBreaker(),
            Provider.OPENAI: CircuitBreaker(),
        }

    def get(self, provider: Provider) -> CircuitBreaker:
        return self._breakers[provider]


class LLMGateway:
    """Unified gateway for LLM providers with fallback chains."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._providers: dict[Provider, BaseLLMProvider] = {}
        self._circuit_breakers = LLMCircuitBreakers()
        self._usage_stats: dict[str, dict[str, int]] = {}

    def _get_provider(self, provider: Provider) -> BaseLLMProvider | None:
        if provider not in self._providers:
            created = self._create_provider(provider)
            if created is not None:
                self._providers[provider] = created
        return self._providers.get(provider)

    def _create_provider(self, provider: Provider) -> BaseLLMProvider | None:
        if provider == Provider.GITHUB_MODELS:
            if self.settings.GITHUB_TOKEN:
                return GitHubModelsProvider(self.settings)
        elif provider == Provider.GROQ:
            if self.settings.GROQ_API_KEY:
                return GroqProvider(self.settings)
        elif provider == Provider.OPENAI:
            if self.settings.OPENAI_API_KEY:
                return OpenAIProvider(self.settings)
        return None

    def _get_fallback_chain(self, agent: AgentType) -> list[Provider]:
        """Get the fallback chain for an agent type."""
        if agent == AgentType.MONITOR:
            primary = getattr(self.settings, "MONITOR_AGENT_PRIMARY_PROVIDER", "github_models")
            fallback = getattr(self.settings, "MONITOR_AGENT_FALLBACK_PROVIDER", "groq")
        elif agent == AgentType.DIAGNOSIS:
            primary = getattr(self.settings, "DIAGNOSIS_AGENT_PRIMARY_PROVIDER", "groq")
            fallback = getattr(self.settings, "DIAGNOSIS_AGENT_FALLBACK_PROVIDER", "github_models")
        elif agent == AgentType.RISK:
            primary = getattr(self.settings, "RISK_AGENT_PRIMARY_PROVIDER", "github_models")
            fallback = getattr(self.settings, "RISK_AGENT_FALLBACK_PROVIDER", "groq")
        elif agent == AgentType.AUTOFIX:
            primary = getattr(self.settings, "AUTOFIX_AGENT_PRIMARY_PROVIDER", "github_models")
            fallback = getattr(self.settings, "AUTOFIX_AGENT_FALLBACK_PROVIDER", "groq")
        else:
            return [Provider.GITHUB_MODELS, Provider.GROQ, Provider.OPENAI]

        chain = []
        try:
            chain.append(Provider(primary))
        except ValueError:
            pass
        try:
            chain.append(Provider(fallback))
        except ValueError:
            pass

        # Add remaining providers
        for p in Provider:
            if p not in chain:
                chain.append(p)

        return chain

    async def complete(
        self,
        agent: AgentType,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Complete with automatic fallback."""
        chain = self._get_fallback_chain(agent)

        last_error: Exception | None = None
        for provider in chain:
            breaker = self._circuit_breakers.get(provider)
            if not breaker.can_execute():
                logger.warning("circuit_breaker_open", provider=provider.value, agent=agent.value)
                continue

            llm_provider = self._get_provider(provider)
            if not llm_provider:
                continue

            if model is None:
                model = llm_provider.get_default_model()

            request = LLMRequest(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )

            try:
                response = await llm_provider.complete(request)
                breaker.record_success()
                self._record_usage(agent, provider, response.usage or {})
                return response
            except LLMProviderError as exc:
                logger.warning(
                    "llm_provider_failed",
                    provider=provider.value,
                    agent=agent.value,
                    error=str(exc),
                )
                breaker.record_failure()
                last_error = exc
                continue

        raise LLMProviderError(
            Provider.GITHUB_MODELS,
            f"All providers failed for agent {agent.value}",
            last_error,
        )

    def _record_usage(self, agent: AgentType, provider: Provider, usage: dict[str, int]) -> None:
        key = f"{agent.value}:{provider.value}"
        if key not in self._usage_stats:
            self._usage_stats[key] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "requests": 0,
            }
        self._usage_stats[key]["prompt_tokens"] += usage.get("prompt_tokens", 0)
        self._usage_stats[key]["completion_tokens"] += usage.get("completion_tokens", 0)
        self._usage_stats[key]["total_tokens"] += usage.get("total_tokens", 0)
        self._usage_stats[key]["requests"] += 1

    def get_usage_stats(self) -> dict[str, dict[str, int]]:
        return self._usage_stats.copy()


# Global gateway instance
_llm_gateway: LLMGateway | None = None


def get_llm_gateway(settings: Settings) -> LLMGateway:
    """Get or create the global LLM gateway instance."""
    global _llm_gateway
    if _llm_gateway is None:
        _llm_gateway = LLMGateway(settings)
    return _llm_gateway
