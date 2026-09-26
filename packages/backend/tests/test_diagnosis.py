"""Tests for diagnosis service."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipelineiq.services.diagnosis import (
    DiagnosisResult,
    apply_diagnosis_to_pipeline_run,
    build_diagnosis_prompt,
    format_diff_for_llm,
    run_diagnosis,
)


class MockSettings:
    GITHUB_TOKEN = "test-token"
    GITHUB_MODELS_API_BASE_URL = "https://models.github.ai/inference"
    GROQ_API_KEY = "test-groq-key"
    GROQ_API_BASE_URL = "https://api.groq.com/openai/v1"
    OPENAI_API_KEY = "test-openai-key"
    OPENAI_API_BASE_URL = "https://api.openai.com/v1"
    DIAGNOSIS_AGENT_PRIMARY_PROVIDER = "groq"
    DIAGNOSIS_AGENT_FALLBACK_PROVIDER = "github_models"


class MockPipelineRun:
    def __init__(self):
        self.monitor_logs_excerpt = [
            "Running tests...",
            "test_user_login FAILED",
            "AssertionError: Expected True, got False",
        ]
        self.monitor_summary = "Test Failure: Detected 1 error(s) in workflow logs"
        self.repository_full_name = "owner/repo"
        self.commit_sha = "abc123def456"
        self.installation_id = 12345
        self.workflow_name = "CI Pipeline"
        self.branch = "feature/test"
        self.diagnosis_report = None
        self.diagnosis_report_json = {}
        self.diagnosis_provider = None
        self.diagnosis_model = None


class MockGitHubAppClient:
    async def get_compare(self, installation_id, owner, repo, base, head):
        return {
            "files": [
                {
                    "filename": "src/auth.py",
                    "status": "modified",
                    "additions": 10,
                    "deletions": 5,
                    "patch": "@@ -1,5 +1,10 @@\n def login():\n+    validate_input()\n     return authenticate()",
                }
            ]
        }


@pytest.fixture
def mock_settings():
    return MockSettings()


@pytest.fixture
def mock_client():
    return MockGitHubAppClient()


@pytest.fixture
def pipeline_run():
    return MockPipelineRun()


def test_format_diff_for_llm():
    diff_data = {
        "files": [
            {
                "filename": "src/main.py",
                "status": "modified",
                "additions": 3,
                "deletions": 1,
                "patch": "@@ -1,3 +1,5 @@\n def main():\n+    print('hello')\n     return 0",
            }
        ]
    }
    result = format_diff_for_llm(diff_data)
    assert "src/main.py" in result
    assert "modified" in result
    assert "print('hello')" in result


def test_format_diff_for_llm_empty():
    result = format_diff_for_llm(None)
    assert result == "No diff data available."
    
    result = format_diff_for_llm({"files": []})
    assert result == "No file changes in diff."


def test_build_diagnosis_prompt():
    messages = build_diagnosis_prompt(
        error_logs="Error: test failed",
        diff_text="+ added line\n- removed line",
        workflow_name="Test Workflow",
        branch="main",
    )
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Test Workflow" in messages[1]["content"]
    assert "main" in messages[1]["content"]
    assert "test failed" in messages[1]["content"]
    assert "added line" in messages[1]["content"]


@pytest.mark.asyncio
async def test_run_diagnosis_success(
    mock_settings, mock_client, pipeline_run
):
    # Mock the LLM gateway
    with patch("pipelineiq.services.diagnosis.get_llm_gateway") as mock_get_gateway:
        mock_gateway = AsyncMock()
        mock_get_gateway.return_value = mock_gateway
        
        # Mock successful JSON response
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "error_type": "Test Failure",
            "possible_causes": ["Assertion error in test_user_login"],
            "latest_working_change": "Added validate_input() call in auth.py",
            "suggested_fixes": ["Fix assertion in test_user_login", "Update test expectations"],
        })
        mock_response.provider.value = "groq"
        mock_response.model = "llama-3.3-70b-versatile"
        mock_gateway.complete = AsyncMock(return_value=mock_response)
        
        result = await run_diagnosis(pipeline_run, mock_settings, mock_client)
        
        assert isinstance(result, DiagnosisResult)
        assert result.error_type == "Test Failure"
        assert len(result.possible_causes) == 1
        assert "validate_input" in result.latest_working_change
        assert len(result.suggested_fixes) == 2
        assert result.provider == "groq"


@pytest.mark.asyncio
async def test_run_diagnosis_invalid_json(
    mock_settings, mock_client, pipeline_run
):
    with patch("pipelineiq.services.diagnosis.get_llm_gateway") as mock_get_gateway:
        mock_gateway = AsyncMock()
        mock_get_gateway.return_value = mock_gateway
        
        # Mock invalid JSON response
        mock_response = MagicMock()
        mock_response.content = "This is not valid JSON"
        mock_response.provider.value = "groq"
        mock_response.model = "llama-3.3-70b-versatile"
        mock_gateway.complete = AsyncMock(return_value=mock_response)
        
        result = await run_diagnosis(pipeline_run, mock_settings, mock_client)
        
        assert isinstance(result, DiagnosisResult)
        assert result.error_type == "Unknown"
        assert "Failed to parse LLM response as JSON" in result.possible_causes


@pytest.mark.asyncio
async def test_run_diagnosis_without_monitor_logs(
    mock_settings, mock_client
):
    """Test diagnosis with minimal monitor data."""
    run = MockPipelineRun()
    run.monitor_logs_excerpt = []
    run.monitor_summary = "Workflow failed"
    
    with patch("pipelineiq.services.diagnosis.get_llm_gateway") as mock_get_gateway:
        mock_gateway = AsyncMock()
        mock_get_gateway.return_value = mock_gateway
        
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "error_type": "Unknown",
            "possible_causes": ["Insufficient log data"],
            "latest_working_change": "Unknown",
            "suggested_fixes": ["Check workflow logs manually"],
        })
        mock_response.provider.value = "groq"
        mock_response.model = "llama-3.3-70b-versatile"
        mock_gateway.complete = AsyncMock(return_value=mock_response)
        
        result = await run_diagnosis(run, mock_settings, mock_client)
        
        assert isinstance(result, DiagnosisResult)
        assert result.error_type == "Unknown"


def test_apply_diagnosis_to_pipeline_run():
    run = MockPipelineRun()
    result = DiagnosisResult(
        error_type="Test Failure",
        possible_causes=["Cause 1", "Cause 2"],
        latest_working_change="Added validation",
        suggested_fixes=["Fix 1", "Fix 2"],
        provider="groq",
        model="llama-3.3-70b-versatile",
        raw_response='{"error_type": "Test Failure", ...}',
    )
    
    apply_diagnosis_to_pipeline_run(run, result)
    
    assert "Test Failure" in run.diagnosis_report
    assert "Cause 1" in run.diagnosis_report
    assert "Cause 2" in run.diagnosis_report
    assert "Added validation" in run.diagnosis_report
    assert "Fix 1" in run.diagnosis_report
    assert run.diagnosis_report_json["error_type"] == "Test Failure"
    assert run.diagnosis_report_json["possible_causes"] == ["Cause 1", "Cause 2"]
    assert run.diagnosis_provider == "groq"
    assert run.diagnosis_model == "llama-3.3-70b-versatile"