"""Pipeline runtime: stage orchestration for processing GitHub webhook events."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

from pipelineiq.config import Settings
from pipelineiq.models import PipelineRun
from pipelineiq.services.error_detection import detect_failure
from pipelineiq.services.github_app import GitHubAppClient
from pipelineiq.services.risk import assess_risk

logger = structlog.get_logger()


@dataclass
class PipelineStage:
    """Represents a pipeline stage with its handler."""

    name: str
    handler: Callable[[PipelineRun, Settings, GitHubAppClient], Awaitable[None]]
    status_field: str
    error_field: str


class PipelineRuntime:
    """Orchestrates the pipeline stages for processing workflow runs."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = GitHubAppClient(settings)
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._current_tasks: set[asyncio.Task[Any]] = set()

    async def start(self) -> None:
        """Start the pipeline runtime."""
        self._running = True
        logger.info("pipeline_runtime_started", kafka_enabled=self.settings.KAFKA_ENABLED)

    async def stop(self) -> None:
        """Stop the pipeline runtime gracefully."""
        logger.info("pipeline_runtime_stopping")
        self._running = False
        self._shutdown_event.set()

        # Wait for in-flight tasks to complete (with timeout)
        if self._current_tasks:
            logger.info("waiting_for_inflight_tasks", count=len(self._current_tasks))
            done, pending = await asyncio.wait(
                self._current_tasks, timeout=30, return_when=asyncio.ALL_COMPLETED
            )
            if pending:
                logger.warning("tasks_did_not_complete_in_time", count=len(pending))
                for task in pending:
                    task.cancel()

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        """Context manager for lifespan management."""
        await self.start()
        try:
            yield
        finally:
            await self.stop()

    async def process_event(
        self,
        delivery_id: str,
        _event_type: str,
        _payload: dict[str, Any],
        _raw_payload: dict[str, Any],
    ) -> None:
        """Process a webhook event through the pipeline stages."""
        # Find the pipeline run
        pipeline_run = await PipelineRun.find_one(PipelineRun.delivery_id == delivery_id)
        if not pipeline_run:
            logger.warning("pipeline_run_not_found", delivery_id=delivery_id)
            return

        if pipeline_run.workspace_id is None:
            logger.warning("pipeline_run_missing_workspace", delivery_id=delivery_id)
            return

        # Get installation ID
        installation_id = pipeline_run.installation_id
        if not installation_id:
            logger.warning("pipeline_run_missing_installation", delivery_id=delivery_id)
            return

        # Process stages sequentially
        stages = self._get_stages()
        for stage in stages:
            if not self._running:
                logger.info("pipeline_stopped_aborting", delivery_id=delivery_id)
                break

            await self._run_stage(pipeline_run, stage, installation_id)

    def _get_stages(self) -> list[PipelineStage]:
        """Get the ordered list of pipeline stages."""
        return [
            PipelineStage(
                name="monitor",
                handler=self._run_monitor,
                status_field="monitor_status",
                error_field="monitor_error",
            ),
            PipelineStage(
                name="diagnosis",
                handler=self._run_diagnosis,
                status_field="diagnosis_status",
                error_field="diagnosis_error",
            ),
            PipelineStage(
                name="risk",
                handler=self._run_risk,
                status_field="risk_status",
                error_field="risk_error",
            ),
            PipelineStage(
                name="autofix",
                handler=self._run_autofix,
                status_field="autofix_status",
                error_field="autofix_error",
            ),
        ]

    async def _run_stage(
        self,
        pipeline_run: PipelineRun,
        stage: PipelineStage,
        _installation_id: int,
    ) -> None:
        """Run a single pipeline stage with error handling."""
        setattr(pipeline_run, stage.status_field, "running")
        pipeline_run.updated_at = datetime.now(UTC)
        await pipeline_run.save()

        logger.info("stage_started", stage=stage.name, delivery_id=pipeline_run.delivery_id)

        try:
            await stage.handler(pipeline_run, self.settings, self.client)
            setattr(pipeline_run, stage.status_field, "completed")
            pipeline_run.updated_at = datetime.now(UTC)
            await pipeline_run.save()
            logger.info("stage_completed", stage=stage.name, delivery_id=pipeline_run.delivery_id)
        except Exception as exc:
            logger.exception("stage_failed", stage=stage.name, delivery_id=pipeline_run.delivery_id)
            setattr(pipeline_run, stage.status_field, "failed")
            setattr(pipeline_run, stage.error_field, str(exc))
            pipeline_run.updated_at = datetime.now(UTC)
            await pipeline_run.save()

    async def _run_monitor(
        self,
        pipeline_run: PipelineRun,
        _settings: Settings,
        client: GitHubAppClient,
    ) -> None:
        """Monitor stage: fetch logs and detect failures."""
        if not pipeline_run.run_id:
            pipeline_run.monitor_summary = "No workflow run ID"
            pipeline_run.health_status = "unknown"
            return

        # Fetch workflow logs
        if not pipeline_run.repository_full_name:
            raise ValueError("Missing repository_full_name")

        owner, repo = pipeline_run.repository_full_name.split("/", 1)
        logs = await client.get_workflow_run_logs(
            installation_id=pipeline_run.installation_id or 0,
            owner=owner,
            repo=repo,
            run_id=pipeline_run.run_id,
        )

        # Detect failure
        health_status, summary, excerpts = detect_failure(logs)

        pipeline_run.health_status = health_status
        pipeline_run.monitor_summary = summary
        pipeline_run.monitor_logs_excerpt = excerpts
        pipeline_run.monitor_report_json = {
            "health_status": health_status,
            "summary": summary,
            "excerpt_count": len(excerpts),
        }
        pipeline_run.monitor_model = "deterministic"
        pipeline_run.monitor_provider = "pipelineiq"

    async def _run_diagnosis(
        self,
        pipeline_run: PipelineRun,
        _settings: Settings,
        _client: GitHubAppClient,
    ) -> None:
        """Diagnosis stage: analyze failure with LLM."""
        # TODO: Implement LLM-based diagnosis
        # For now, just mark as completed with a placeholder
        pipeline_run.diagnosis_status = "completed"
        pipeline_run.diagnosis_report = "Diagnosis not yet implemented"
        pipeline_run.diagnosis_report_json = {"status": "not_implemented"}
        pipeline_run.diagnosis_provider = "placeholder"
        pipeline_run.diagnosis_model = "placeholder"

    async def _run_risk(
        self,
        pipeline_run: PipelineRun,
        _settings: Settings,
        _client: GitHubAppClient,
    ) -> None:
        """Risk stage: assess deployment risk."""
        # Build signals from pipeline run
        signals = {
            "branch": pipeline_run.branch or "unknown",
            "files_changed": 0,
            "lines_changed": 0,
            "touches_sensitive_files": False,
            "tests_failed": pipeline_run.health_status == "failed",
            "has_required_review": False,
            "prior_similar_failures": 0,
        }

        # TODO: Extract actual signals from GitHub API
        # For now, use defaults with failed tests signal

        # Import risk contracts
        from pipelineiq.contracts import RiskProfile, RiskSignals

        risk_signals = RiskSignals(**signals)
        risk_profile = RiskProfile()  # Use workspace profile later

        assessment = assess_risk(risk_signals, risk_profile)

        pipeline_run.risk_score = assessment.score
        pipeline_run.risk_band = assessment.band.value
        pipeline_run.risk_report_json = {
            "score": assessment.score,
            "band": assessment.band.value,
            "action": assessment.action.value,
            "factors": [
                {"name": f.name, "points": f.points, "reason": f.reason}
                for f in assessment.factors
            ],
        }
        pipeline_run.risk_inputs_json = signals
        pipeline_run.risk_provider = "deterministic"
        pipeline_run.risk_model = "pipelineiq"

        # Store policy action for autofix stage
        pipeline_run.autofix_mode = assessment.action.value

    async def _run_autofix(
        self,
        pipeline_run: PipelineRun,
        _settings: Settings,
        _client: GitHubAppClient,
    ) -> None:
        """Auto-fix stage: generate fix and create PR if needed."""
        # TODO: Implement auto-fix logic
        # For now, just mark as completed with policy action
        if pipeline_run.autofix_mode == "auto_fix":
            pipeline_run.autofix_status = "completed"
            pipeline_run.autofix_mode = "auto_fix"
        elif pipeline_run.autofix_mode == "approval_required":
            pipeline_run.autofix_status = "awaiting_approval"
        elif pipeline_run.autofix_mode == "block_only":
            pipeline_run.autofix_status = "blocked"
        else:
            pipeline_run.autofix_status = "skipped"


# Global runtime instance
_pipeline_runtime: PipelineRuntime | None = None


def get_pipeline_runtime(settings: Settings) -> PipelineRuntime:
    """Get or create the global pipeline runtime instance."""
    global _pipeline_runtime
    if _pipeline_runtime is None:
        _pipeline_runtime = PipelineRuntime(settings)
    return _pipeline_runtime


async def process_pipeline_run_inline(
    delivery_id: str,
    settings: Settings,
) -> None:
    """Process a pipeline run inline (without Kafka)."""
    runtime = get_pipeline_runtime(settings)
    # The event was already processed by webhook handler, just run the pipeline
    pipeline_run = await PipelineRun.find_one(PipelineRun.delivery_id == delivery_id)
    if not pipeline_run:
        return

    installation_id = pipeline_run.installation_id
    if not installation_id:
        return

    # Get the raw event from the pipeline run
    raw_event = pipeline_run.raw_event or {}
    await runtime.process_event(
        delivery_id=delivery_id,
        _event_type=pipeline_run.event_type,
        _payload=raw_event,
        _raw_payload=raw_event,
    )