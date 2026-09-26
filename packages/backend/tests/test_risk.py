import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from pipelineiq.contracts import PolicyAction, RiskBand, RiskProfile, RiskSignals
from pipelineiq.main import app
from pipelineiq.services.risk import assess_risk


def test_low_risk_change_is_eligible_for_auto_fix() -> None:
    result = assess_risk(
        RiskSignals(
            branch="feature/docs",
            files_changed=1,
            lines_changed=10,
            tests_failed=False,
            has_required_review=True,
        ),
        RiskProfile(),
    )

    assert result.score == 0
    assert result.band is RiskBand.LOW
    assert result.action is PolicyAction.AUTO_FIX


def test_sensitive_production_change_is_blocked() -> None:
    result = assess_risk(
        RiskSignals(
            branch="main",
            files_changed=12,
            lines_changed=500,
            touches_sensitive_files=True,
            tests_failed=True,
            has_required_review=False,
            prior_similar_failures=3,
        ),
        RiskProfile(),
    )

    assert result.score == 100
    assert result.band is RiskBand.HIGH
    assert result.action is PolicyAction.BLOCK_ONLY


def test_profile_rejects_inverted_thresholds() -> None:
    with pytest.raises(ValidationError):
        RiskProfile(auto_fix_below=70, require_approval_above=60)


@pytest.mark.asyncio
async def test_risk_endpoint_returns_explainable_result() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/risk/assess",
            json={
                "signals": {
                    "branch": "main",
                    "files_changed": 3,
                    "lines_changed": 100,
                    "touches_sensitive_files": False,
                    "tests_failed": True,
                    "has_required_review": False,
                    "prior_similar_failures": 0,
                }
            },
        )

    assert response.status_code == 200
    assert response.json()["score"] == 58
    assert response.json()["action"] == "approval_required"
    assert len(response.json()["factors"]) == 5
