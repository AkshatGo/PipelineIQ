"""Audit log service: append-only incident event store with actor typing."""

from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId

from pipelineiq.models import IncidentEvent


class AuditService:
    """Service for logging and querying audit events."""

    EVENT_TYPES = {
        # Incident lifecycle
        "incident.created",
        "incident.status_changed",
        "incident.resolved",
        "incident.closed",
        # Workspace
        "workspace.opened",
        "workspace.document_edited",
        "workspace.document_created",
        "workspace.document_deleted",
        "workspace.participant_joined",
        "workspace.participant_left",
        "workspace.synced",
        "workspace.offline",
        # Version control
        "version.checkpoint_created",
        "version.restored",
        "version.compared",
        # AI actions
        "ai.diagnosis_generated",
        "ai.fix_proposed",
        "ai.fix_applied",
        "ai.risk_assessed",
        "ai.suggestion_accepted",
        "ai.suggestion_rejected",
        "ai.suggestion_modified",
        # Human actions
        "human.applied_fix",
        "human.modified_file",
        "human.added_comment",
        "human.requested_review",
        "human.approved_changes",
        "human.rejected_changes",
        # CI/CD
        "ci.validation_started",
        "ci.validation_passed",
        "ci.validation_failed",
        "ci.re_run_triggered",
        # GitHub
        "github.pr_created",
        "github.pr_updated",
        "github.pr_merged",
        "github.pr_closed",
        "github.webhook_received",
    }

    ACTOR_TYPES = {"human", "ai", "system", "webhook"}

    async def log_event(
        self,
        incident_id: PydanticObjectId,
        workspace_id: PydanticObjectId,
        actor_id: PydanticObjectId,
        actor_type: str,
        actor_name: str,
        event_type: str,
        action: str,
        description: str,
        document_id: PydanticObjectId | None = None,
        version_id: PydanticObjectId | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> IncidentEvent:
        """Log an incident event to the audit log."""
        if actor_type not in self.ACTOR_TYPES:
            raise ValueError(f"Invalid actor_type: {actor_type}. Must be one of {self.ACTOR_TYPES}")

        event = IncidentEvent(
            incident_id=incident_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_name=actor_name,
            type=event_type,
            action=action,
            description=description,
            document_id=document_id,
            version_id=version_id,
            before=before or {},
            after=after or {},
            metadata=metadata or {},
            correlation_id=correlation_id,
            causation_id=causation_id,
        )
        await event.insert()
        return event

    # Convenience methods for common events

    async def log_incident_created(
        self,
        incident_id: PydanticObjectId,
        workspace_id: PydanticObjectId,
        actor_id: PydanticObjectId,
        actor_name: str,
    ) -> IncidentEvent:
        return await self.log_event(
            incident_id=incident_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            actor_type="system",
            actor_name=actor_name,
            event_type="incident.created",
            action="create",
            description="Incident workspace created from failed pipeline run",
        )

    async def log_document_edited(
        self,
        incident_id: PydanticObjectId,
        workspace_id: PydanticObjectId,
        actor_id: PydanticObjectId,
        actor_type: str,
        actor_name: str,
        document_id: PydanticObjectId,
        path: str,
        before_content: str,
        after_content: str,
    ) -> IncidentEvent:
        return await self.log_event(
            incident_id=incident_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_name=actor_name,
            event_type="workspace.document_edited",
            action="edit",
            description=f"Modified file: {path}",
            document_id=document_id,
            before={"content": before_content[:500]},
            after={"content": after_content[:500]},
            metadata={"path": path},
        )

    async def log_checkpoint_created(
        self,
        incident_id: PydanticObjectId,
        workspace_id: PydanticObjectId,
        actor_id: PydanticObjectId,
        actor_type: str,
        actor_name: str,
        document_id: PydanticObjectId,
        version_id: PydanticObjectId,
        message: str,
        tags: list[str],
    ) -> IncidentEvent:
        return await self.log_event(
            incident_id=incident_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_name=actor_name,
            event_type="version.checkpoint_created",
            action="checkpoint",
            description=f"Created checkpoint: {message}",
            document_id=document_id,
            version_id=version_id,
            metadata={"tags": tags, "message": message},
        )

    async def log_version_restored(
        self,
        incident_id: PydanticObjectId,
        workspace_id: PydanticObjectId,
        actor_id: PydanticObjectId,
        actor_type: str,
        actor_name: str,
        document_id: PydanticObjectId,
        version_id: PydanticObjectId,
        restored_from_version: int,
    ) -> IncidentEvent:
        return await self.log_event(
            incident_id=incident_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_name=actor_name,
            event_type="version.restored",
            action="restore",
            description=f"Restored document to version {restored_from_version}",
            document_id=document_id,
            version_id=version_id,
            metadata={"restored_from_version": restored_from_version},
        )

    async def log_ai_suggestion(
        self,
        incident_id: PydanticObjectId,
        workspace_id: PydanticObjectId,
        agent_type: str,
        suggestion_type: str,  # "diagnosis", "fix", "risk"
        description: str,
        confidence: float,
        metadata: dict[str, Any] | None = None,
    ) -> IncidentEvent:
        event_type = f"ai.{suggestion_type}_proposed"
        return await self.log_event(
            incident_id=incident_id,
            workspace_id=workspace_id,
            actor_id=PydanticObjectId(),  # System AI actor
            actor_type="ai",
            actor_name=f"PipelineIQ {agent_type} Agent",
            event_type=event_type,
            action="suggest",
            description=description,
            metadata={"confidence": confidence, "agent_type": agent_type, **(metadata or {})},
        )

    async def log_ai_suggestion_outcome(
        self,
        incident_id: PydanticObjectId,
        workspace_id: PydanticObjectId,
        actor_id: PydanticObjectId,
        actor_type: str,
        actor_name: str,
        suggestion_type: str,
        outcome: str,  # "accepted", "rejected", "modified"
        document_id: PydanticObjectId | None = None,
    ) -> IncidentEvent:
        event_type = f"ai.suggestion_{outcome}"
        return await self.log_event(
            incident_id=incident_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_name=actor_name,
            event_type=event_type,
            action=outcome,
            description=f"{outcome.capitalize()} AI {suggestion_type} suggestion",
            document_id=document_id,
        )

    async def log_human_action(
        self,
        incident_id: PydanticObjectId,
        workspace_id: PydanticObjectId,
        actor_id: PydanticObjectId,
        actor_name: str,
        action: str,
        description: str,
        document_id: PydanticObjectId | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> IncidentEvent:
        return await self.log_event(
            incident_id=incident_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            actor_type="human",
            actor_name=actor_name,
            event_type=f"human.{action}",
            action=action,
            description=description,
            document_id=document_id,
            metadata=metadata,
        )

    async def log_validation_started(
        self,
        incident_id: PydanticObjectId,
        workspace_id: PydanticObjectId,
        validation_run_id: PydanticObjectId,
        triggered_by: PydanticObjectId,
    ) -> IncidentEvent:
        return await self.log_event(
            incident_id=incident_id,
            workspace_id=workspace_id,
            actor_id=triggered_by,
            actor_type="system",
            actor_name="PipelineIQ Validation System",
            event_type="ci.validation_started",
            action="start",
            description="CI/CD validation pipeline started",
            metadata={"validation_run_id": str(validation_run_id)},
        )

    async def log_validation_completed(
        self,
        incident_id: PydanticObjectId,
        workspace_id: PydanticObjectId,
        validation_run_id: PydanticObjectId,
        status: str,  # "passed" | "failed"
        stage_results: list[dict[str, Any]],
    ) -> IncidentEvent:
        return await self.log_event(
            incident_id=incident_id,
            workspace_id=workspace_id,
            actor_id=PydanticObjectId(),  # System actor
            actor_type="system",
            actor_name="PipelineIQ Validation System",
            event_type=f"ci.validation_{status}",
            action="complete",
            description=f"CI/CD validation {status}",
            metadata={
                "validation_run_id": str(validation_run_id),
                "stages": stage_results,
            },
        )

    async def log_github_pr_event(
        self,
        incident_id: PydanticObjectId,
        workspace_id: PydanticObjectId,
        actor_id: PydanticObjectId,
        actor_type: str,
        actor_name: str,
        event_type: str,  # "created", "updated", "merged", "closed"
        pr_number: int,
        pr_url: str,
    ) -> IncidentEvent:
        return await self.log_event(
            incident_id=incident_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_name=actor_name,
            event_type=f"github.pr_{event_type}",
            action=event_type,
            description=f"Pull request #{pr_number} {event_type}",
            metadata={"pr_number": pr_number, "pr_url": pr_url},
        )


# Global instance
_audit_service: AuditService | None = None


def get_audit_service() -> AuditService:
    """Get or create the global audit service instance."""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service