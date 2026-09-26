"""Tests for pipeline_runtime service."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipelineiq.services.pipeline_runtime import PipelineRuntime


class MockSettings:
    KAFKA_ENABLED = False
    GITHUB_API_URL = "https://api.github.com"


class MockGitHubAppClient:
    async def get_workflow_run_logs(self, **_kwargs: Any) -> str:
        return "Running tests...\ntest_example FAILED\nAssertionError: Expected True"


class MockPipelineRun:
    def __init__(self) -> None:
        self.delivery_id = "delivery-123"
        self.workspace_id = MagicMock()
        self.installation_id = 12345
        self.run_id = 67890
        self.repository_full_name = "owner/repo"
        self.branch = "main"
        self.health_status = "unknown"
        self.monitor_status = "pending"
        self.diagnosis_status = "pending"
        self.risk_status = "pending"
        self.autofix_status = "pending"
        self.updated_at = None
        self.save = AsyncMock()
        self.monitor_summary = None
        self.monitor_logs_excerpt = []
        self.monitor_report_json = {}
        self.risk_score = None
        self.risk_band = None
        self.risk_report_json = {}
        self.risk_inputs_json = {}
        self.autofix_mode = None


@pytest.fixture
def mock_settings() -> MockSettings:
    return MockSettings()


@pytest.fixture
def mock_client() -> MockGitHubAppClient:
    return MockGitHubAppClient()


@pytest.fixture
def pipeline_run() -> MockPipelineRun:
    return MockPipelineRun()


@pytest.mark.asyncio
async def test_pipeline_runtime_start_stop(mock_settings: MockSettings) -> None:
    runtime = PipelineRuntime(mock_settings)
    await runtime.start()
    assert runtime._running is True
    await runtime.stop()
    assert runtime._running is False


@pytest.mark.asyncio
async def test_get_stages(mock_settings: MockSettings) -> None:
    runtime = PipelineRuntime(mock_settings)
    stages = runtime._get_stages()
    assert len(stages) == 4
    assert [s.name for s in stages] == ["monitor", "diagnosis", "risk", "autofix"]


@pytest.mark.asyncio
async def test_run_monitor_stage(
    mock_settings: MockSettings,
    mock_client: MockGitHubAppClient,
    pipeline_run: MockPipelineRun,
) -> None:
    runtime = PipelineRuntime(mock_settings)
    runtime.client = mock_client

    # Test the monitor handler directly (it doesn't set status, that's done by _run_stage)
    await runtime._run_monitor(pipeline_run, mock_settings, mock_client)

    # Check the attributes that _run_monitor actually sets
    assert pipeline_run.health_status == "failed"
    assert pipeline_run.monitor_summary is not None
    assert "Test Failure" in pipeline_run.monitor_summary
    assert len(pipeline_run.monitor_logs_excerpt) > 0
    pipeline_run.save.assert_not_called()  # _run_monitor doesn't call save


@pytest.mark.asyncio
async def test_run_risk_stage(
    mock_settings: MockSettings,
    mock_client: MockGitHubAppClient,
    pipeline_run: MockPipelineRun,
) -> None:
    runtime = PipelineRuntime(mock_settings)

    # Test the risk handler directly
    await runtime._run_risk(pipeline_run, mock_settings, mock_client)

    # Check the attributes that _run_risk actually sets
    assert pipeline_run.risk_score is not None
    assert pipeline_run.risk_band is not None
    assert pipeline_run.risk_report_json is not None
    assert pipeline_run.autofix_mode is not None
    pipeline_run.save.assert_not_called()  # _run_risk doesn't call save


@pytest.mark.asyncio
async def test_process_event_pipeline_run_not_found(mock_settings: MockSettings) -> None:
    runtime = PipelineRuntime(mock_settings)

    with patch("pipelineiq.services.pipeline_runtime.PipelineRun") as mock_pipeline_run_class:
        mock_pipeline_run_class.find_one = AsyncMock(return_value=None)
        # Should not raise, just log warning
        await runtime.process_event(
            delivery_id="nonexistent",
            _event_type="workflow_run",
            _payload={},
            _raw_payload={},
        )


@pytest.mark.asyncio
async def test_process_event_missing_workspace(mock_settings: MockSettings) -> None:
    runtime = PipelineRuntime(mock_settings)

    mock_run = MockPipelineRun()
    mock_run.workspace_id = None

    with patch("pipelineiq.services.pipeline_runtime.PipelineRun") as mock_pipeline_run_class:
        mock_pipeline_run_class.find_one = AsyncMock(return_value=mock_run)
        await runtime.process_event(
            delivery_id="delivery-123",
            _event_type="workflow_run",
            _payload={},
            _raw_payload={},
        )


@pytest.mark.asyncio
async def test_process_event_missing_installation(mock_settings: MockSettings) -> None:
    runtime = PipelineRuntime(mock_settings)

    mock_run = MockPipelineRun()
    mock_run.installation_id = None

    with patch("pipelineiq.services.pipeline_runtime.PipelineRun") as mock_pipeline_run_class:
        mock_pipeline_run_class.find_one = AsyncMock(return_value=mock_run)
        await runtime.process_event(
            delivery_id="delivery-123",
            _event_type="workflow_run",
            _payload={},
            _raw_payload={},
        )