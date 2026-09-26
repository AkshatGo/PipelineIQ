"""Tests for LLM gateway."""

from unittest.mock import MagicMock

import pytest

from pipelineiq.services.llm_gateway import (
    AgentType,
    CircuitBreaker,
    LLMCircuitBreakers,
    LLMGateway,
    LLMProviderError,
    LLMResponse,
    Provider,
)


class MockSettings:
    GITHUB_TOKEN = "test-token"
    GITHUB_MODELS_API_BASE_URL = "https://models.github.ai/inference"
    GROQ_API_KEY = "test-groq-key"
    GROQ_API_BASE_URL = "https://api.groq.com/openai/v1"
    OPENAI_API_KEY = "test-openai-key"
    OPENAI_API_BASE_URL = "https://api.openai.com/v1"
    MONITOR_AGENT_PRIMARY_PROVIDER = "github_models"
    MONITOR_AGENT_FALLBACK_PROVIDER = "groq"
    DIAGNOSIS_AGENT_PRIMARY_PROVIDER = "groq"
    DIAGNOSIS_AGENT_FALLBACK_PROVIDER = "github_models"
    RISK_AGENT_PRIMARY_PROVIDER = "github_models"
    RISK_AGENT_FALLBACK_PROVIDER = "groq"
    AUTOFIX_AGENT_PRIMARY_PROVIDER = "github_models"
    AUTOFIX_AGENT_FALLBACK_PROVIDER = "groq"


@pytest.fixture
def mock_settings():
    return MockSettings()


def test_circuit_breaker_initial_state():
    cb = CircuitBreaker()
    assert cb.state == "closed"
    assert cb.can_execute() is True


def test_circuit_breaker_opens_after_threshold():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == "closed"
    cb.record_failure()
    assert cb.state == "open"
    assert cb.can_execute() is False


def test_circuit_breaker_half_open_after_timeout():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == "open"
    import time
    time.sleep(0.02)
    assert cb.can_execute() is True
    assert cb.state == "half-open"


def test_circuit_breakers_manager():
    breakers = LLMCircuitBreakers()
    for provider in Provider:
        breaker = breakers.get(provider)
        assert isinstance(breaker, CircuitBreaker)
        assert breaker.state == "closed"


@pytest.mark.asyncio
async def test_llm_gateway_initialization(mock_settings):
    gateway = LLMGateway(mock_settings)
    assert gateway._get_provider(Provider.GITHUB_MODELS) is not None
    assert gateway._get_provider(Provider.GROQ) is not None
    assert gateway._get_provider(Provider.OPENAI) is not None


def test_fallback_chain_for_agents(mock_settings):
    gateway = LLMGateway(mock_settings)
    
    chain = gateway._get_fallback_chain(AgentType.MONITOR)
    assert Provider.GITHUB_MODELS in chain
    assert Provider.GROQ in chain
    
    chain = gateway._get_fallback_chain(AgentType.DIAGNOSIS)
    assert Provider.GROQ in chain
    assert Provider.GITHUB_MODELS in chain
    
    chain = gateway._get_fallback_chain(AgentType.RISK)
    assert Provider.GITHUB_MODELS in chain
    
    chain = gateway._get_fallback_chain(AgentType.AUTOFIX)
    assert Provider.GITHUB_MODELS in chain


@pytest.mark.asyncio
async def test_llm_gateway_complete_with_mock_provider(mock_settings):
    gateway = LLMGateway(mock_settings)
    
    # Mock the provider
    mock_provider = MagicMock()
    mock_provider.get_default_model.return_value = "test-model"
    
    async def mock_complete(request):
        return LLMResponse(
            content="Test response",
            provider=Provider.GITHUB_MODELS,
            model=request.model,
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            latency_ms=100,
        )
    
    mock_provider.complete = mock_complete
    gateway._providers[Provider.GITHUB_MODELS] = mock_provider
    
    response = await gateway.complete(
        agent=AgentType.MONITOR,
        messages=[{"role": "user", "content": "test"}],
    )
    
    assert response.content == "Test response"
    assert response.provider == Provider.GITHUB_MODELS
    assert response.usage["total_tokens"] == 30


@pytest.mark.asyncio
async def test_llm_gateway_fallback_on_failure(mock_settings):
    gateway = LLMGateway(mock_settings)
    
    # First provider fails
    mock_fail = MagicMock()
    mock_fail.get_default_model.return_value = "fail-model"
    async def fail_complete(request):
        raise LLMProviderError(Provider.GITHUB_MODELS, "API Error")
    mock_fail.complete = fail_complete
    gateway._providers[Provider.GITHUB_MODELS] = mock_fail
    
    # Second provider succeeds
    mock_success = MagicMock()
    mock_success.get_default_model.return_value = "success-model"
    async def success_complete(request):
        return LLMResponse(
            content="Success response",
            provider=Provider.GROQ,
            model=request.model,
            usage={"prompt_tokens": 5, "completion_tokens": 15, "total_tokens": 20},
            latency_ms=50,
        )
    mock_success.complete = success_complete
    gateway._providers[Provider.GROQ] = mock_success
    
    response = await gateway.complete(
        agent=AgentType.MONITOR,
        messages=[{"role": "user", "content": "test"}],
    )
    
    assert response.content == "Success response"
    assert response.provider == Provider.GROQ


@pytest.mark.asyncio
async def test_llm_gateway_all_providers_fail(mock_settings):
    gateway = LLMGateway(mock_settings)
    
    for provider in Provider:
        mock_provider = MagicMock()
        mock_provider.get_default_model.return_value = f"{provider.value}-model"
        async def fail_complete(request):
            raise LLMProviderError(provider, "API Error")
        mock_provider.complete = fail_complete
        gateway._providers[provider] = mock_provider
    
    with pytest.raises(LLMProviderError) as exc_info:
        await gateway.complete(
            agent=AgentType.MONITOR,
            messages=[{"role": "user", "content": "test"}],
        )
    
    assert "All providers failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_circuit_breaker_prevents_calls(mock_settings):
    gateway = LLMGateway(mock_settings)
    
    # Open the circuit breaker for GITHUB_MODELS
    breaker = gateway._circuit_breakers.get(Provider.GITHUB_MODELS)
    for _ in range(5):
        breaker.record_failure()
    
    assert breaker.state == "open"
    assert breaker.can_execute() is False
    
    # Should skip GITHUB_MODELS and try GROQ
    mock_success = MagicMock()
    mock_success.get_default_model.return_value = "groq-model"
    async def success_complete(request):
        return LLMResponse(
            content="Groq response",
            provider=Provider.GROQ,
            model=request.model,
            usage={"total_tokens": 10},
            latency_ms=10,
        )
    mock_success.complete = success_complete
    gateway._providers[Provider.GROQ] = mock_success
    
    response = await gateway.complete(
        agent=AgentType.MONITOR,
        messages=[{"role": "user", "content": "test"}],
    )
    
    assert response.provider == Provider.GROQ


def test_usage_stats_tracking(mock_settings):
    gateway = LLMGateway(mock_settings)
    
    # Manually record some usage
    gateway._record_usage(
        AgentType.DIAGNOSIS,
        Provider.GITHUB_MODELS,
        {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    )
    
    stats = gateway.get_usage_stats()
    key = f"{AgentType.DIAGNOSIS.value}:{Provider.GITHUB_MODELS.value}"
    assert key in stats
    assert stats[key]["prompt_tokens"] == 100
    assert stats[key]["completion_tokens"] == 50
    assert stats[key]["total_tokens"] == 150
    assert stats[key]["requests"] == 1