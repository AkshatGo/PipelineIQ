"""Tests for autofix service."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipelineiq.services.autofix_service import (
    AutoFixResult,
    build_autofix_prompt,
    build_pr_body,
    format_diff_for_llm,
    generate_autofix,
)


class MockSettings:
    GITHUB_TOKEN = "test-token"
    GITHUB_MODELS_API_BASE_URL = "https://models.github.ai/inference"
    GROQ_API_KEY = "test-groq-key"
    GROQ_API_BASE_URL = "https://api.groq.com/openai/v1"
    OPENAI_API_KEY = "test-openai-key"
    OPENAI_API_BASE_URL = "https://api.openai.com/v1"
    AUTOFIX_AGENT_PRIMARY_PROVIDER = "github_models"
    AUTOFIX_AGENT_FALLBACK_PROVIDER = "groq"


class MockPipelineRun:
    def __init__(self):
        self.diagnosis_report_json = {
            "error_type": "Test Failure",
            "possible_causes": ["Assertion error in test_user_login"],
            "suggested_fixes": ["Fix assertion in test_user_login"],
        }
        self.repository_full_name = "owner/repo"
        self.commit_sha = "abc123def456"
        self.installation_id = 12345
        self.workflow_name = "CI Pipeline"
        self.branch = "feature/test"
        self.risk_score = 25
        self.risk_band = "low"
        self.risk_report_json = {"score": 25, "band": "low", "action": "auto_fix"}
        self.autofix_mode = "auto_fix"
        self.error_summary = "test_user_login FAILED: AssertionError"
        self.monitor_logs_excerpt = ["test_user_login FAILED", "AssertionError: Expected True"]
        self.workspace_id = MagicMock()


class MockGitHubAppClient:
    async def get_compare(self, installation_id, owner, repo, base, head):
        return {
            "files": [
                {
                    "filename": "tests/test_auth.py",
                    "status": "modified",
                    "additions": 3,
                    "deletions": 1,
                    "patch": "@@ -10,7 +10,7 @@\n def test_user_login():\n-    assert user.is_active()\n+    assert user.is_active() == True\n     return True",
                }
            ]
        }

    async def get_file_content(self, installation_id, owner, repo, path, ref):
        return {"content": "ZGVmIHRlc3RfdXNlcl9sb2dpbigpOgogICAgYXNzZXJ0IHVzZXIuaXNfYWN0aXZlKCk="}


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
                "filename": "tests/test_auth.py",
                "status": "modified",
                "additions": 3,
                "deletions": 1,
                "patch": "@@ -10,7 +10,7 @@\n def test_user_login():\n-    assert user.is_active()\n+    assert user.is_active() == True\n     return True",
            }
        ]
    }
    result = format_diff_for_llm(diff_data)
    assert "tests/test_auth.py" in result
    assert "modified" in result
    assert "assert user.is_active() == True" in result


def test_format_diff_for_llm_empty():
    result = format_diff_for_llm(None)
    assert result == "No diff data available."
    
    result = format_diff_for_llm({"files": []})
    assert result == "No file changes in diff."


def test_build_autofix_prompt():
    messages = build_autofix_prompt(
        error_type="Test Failure",
        possible_causes=["Assertion error"],
        diff_text="+ fixed line\n- broken line",
        workflow_name="Test Workflow",
        branch="main",
        suggested_fixes=["Fix assertion"],
    )
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Test Workflow" in messages[1]["content"]
    assert "Test Failure" in messages[1]["content"]
    assert "fixed line" in messages[1]["content"]


def test_build_pr_body():
    run = MockPipelineRun()
    result = AutoFixResult(
        summary="Fixed assertion in test_user_login",
        files=[{"path": "tests/test_auth.py"}],
        provider="github_models",
        model="gpt-4o-mini",
        raw_response="{}",
    )
    execution_id = "exec-123"
    
    body = build_pr_body(run, result, execution_id)
    
    assert "exec-123" in body
    assert "CI Pipeline" in body
    assert "Test Failure" in body
    assert "Fixed assertion" in body
    assert "tests/test_auth.py" in body
    assert "25" in body  # risk score
    assert "low" in body  # risk band


@pytest.mark.asyncio
async def test_generate_autofix_success(
    mock_settings, mock_client, pipeline_run
):
    with patch("pipelineiq.services.autofix_service.get_llm_gateway") as mock_get_gateway:
        mock_gateway = AsyncMock()
        mock_get_gateway.return_value = mock_gateway
        
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "summary": "Fixed assertion in test_user_login",
            "files": [
                {
                    "path": "tests/test_auth.py",
                    "original_content": "assert user.is_active()",
                    "new_content": "assert user.is_active() == True",
                }
            ],
        })
        mock_response.provider.value = "github_models"
        mock_response.model = "gpt-4o-mini"
        mock_gateway.complete = AsyncMock(return_value=mock_response)
        
        result = await generate_autofix(pipeline_run, mock_settings, mock_client)
        
        assert isinstance(result, AutoFixResult)
        assert result.summary == "Fixed assertion in test_user_login"
        assert len(result.files) == 1
        assert result.files[0]["path"] == "tests/test_auth.py"
        assert result.provider == "github_models"


@pytest.mark.asyncio
async def test_generate_autofix_invalid_json(
    mock_settings, mock_client, pipeline_run
):
    with patch("pipelineiq.services.autofix_service.get_llm_gateway") as mock_get_gateway:
        mock_gateway = AsyncMock()
        mock_get_gateway.return_value = mock_gateway
        
        mock_response = MagicMock()
        mock_response.content = "Not valid JSON"
        mock_response.provider.value = "github_models"
        mock_response.model = "gpt-4o-mini"
        mock_gateway.complete = AsyncMock(return_value=mock_response)
        
        result = await generate_autofix(pipeline_run, mock_settings, mock_client)
        
        assert isinstance(result, AutoFixResult)
        assert result.summary == "Failed to parse LLM response"
        assert result.files == []


@pytest.mark.asyncio
async def test_generate_autofix_without_repo(mock_settings):
    """Test auto-fix generation when no repo info available."""
    run = MockPipelineRun()
    run.repository_full_name = None
    
    with patch("pipelineiq.services.autofix_service.get_llm_gateway") as mock_get_gateway:
        mock_gateway = AsyncMock()
        mock_get_gateway.return_value = mock_gateway
        
        mock_response = MagicMock()
        mock_response.content = json.dumps({"summary": "No repo", "files": []})
        mock_response.provider.value = "github_models"
        mock_response.model = "gpt-4o-mini"
        mock_gateway.complete = AsyncMock(return_value=mock_response)
        
        result = await generate_autofix(run, mock_settings, MockGitHubAppClient())
        
        assert isinstance(result, AutoFixResult)