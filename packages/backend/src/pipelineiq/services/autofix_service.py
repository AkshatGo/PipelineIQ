"""Auto-fix service: generates minimal patches and creates PRs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pipelineiq.config import Settings
from pipelineiq.github.github_app_client import GitHubAppClient, GitHubAppError
from pipelineiq.models import AutoFixExecution, AutoFixMemory, PipelineRun
from pipelineiq.services.llm_gateway import AgentType, get_llm_gateway

AUTOFIX_SYSTEM_PROMPT = (
    "You are an expert software engineer. Generate a minimal, safe fix for the "
    "CI/CD failure described below.\n\n"
    "Constraints:\n"
    "- Modify at most 3 files\n"
    "- Make minimal changes - only fix the specific issue\n"
    "- Preserve existing code style and patterns\n"
    "- Add tests if the fix changes behavior\n"
    "- Do not refactor unrelated code\n\n"
    "Output must be valid JSON matching the schema below."
)


AUTOFIX_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "original_content": {"type": "string"},
                    "new_content": {"type": "string"},
                },
                "required": ["path", "original_content", "new_content"],
            },
        },
    },
    "required": ["summary", "files"],
}


@dataclass
class AutoFixResult:
    """Result of auto-fix generation."""

    summary: str
    files: list[dict[str, str]]
    provider: str
    model: str
    raw_response: str


async def fetch_file_content(
    client: GitHubAppClient,
    installation_id: int,
    owner: str,
    repo: str,
    path: str,
    ref: str,
) -> str | None:
    """Fetch a file's content from the repository."""
    try:
        result = await client.get_file_content(installation_id, owner, repo, path, ref)
        if result and "content" in result:
            import base64

            return base64.b64decode(result["content"]).decode("utf-8")
    except Exception:
        pass
    return None


async def get_changed_files_from_diff(
    client: GitHubAppClient,
    installation_id: int,
    owner: str,
    repo: str,
    base_sha: str,
    head_sha: str,
) -> list[dict[str, Any]]:
    """Get list of changed files from the diff."""
    compare = await client.get_compare(installation_id, owner, repo, base_sha, head_sha)
    if not compare:
        return []
    return compare.get("files", [])  # type: ignore[no-any-return]


def build_autofix_prompt(
    error_type: str,
    possible_causes: list[str],
    diff_text: str,
    workflow_name: str,
    branch: str,
    suggested_fixes: list[str],
) -> list[dict[str, str]]:
    """Build the auto-fix prompt for the LLM."""
    user_prompt = f"""Generate a minimal fix for this CI/CD failure:

**Workflow**: {workflow_name}
**Branch**: {branch}
**Error Type**: {error_type}

**Possible Causes**:
{chr(10).join(f"  - {c}" for c in possible_causes)}

**Suggested Fix Directions**:
{chr(10).join(f"  - {f}" for f in suggested_fixes)}

**Git Diff (base -> head)**:
```
{diff_text[:12000]}
```

Provide fix as JSON with "summary" and "files" array containing
"path", "original_content", "new_content"."""

    return [
        {"role": "system", "content": AUTOFIX_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def format_diff_for_llm(diff_data: dict[str, Any] | None) -> str:
    """Format GitHub compare API response for LLM consumption."""
    if not diff_data:
        return "No diff data available."

    files = diff_data.get("files", [])
    if not files:
        return "No file changes in diff."

    parts = []
    for file in files[:10]:
        filename = file.get("filename", "unknown")
        status = file.get("status", "modified")
        patch = file.get("patch", "")
        parts.append(f"=== {filename} ({status}) ===")
        if patch:
            parts.append(patch[:3000])
        else:
            additions = file.get("additions", 0)
            deletions = file.get("deletions", 0)
            parts.append(f"  +{additions} -{deletions} (binary or large file)")

    return "\n".join(parts)


async def generate_autofix(
    pipeline_run: PipelineRun,
    settings: Settings,
    client: GitHubAppClient,
) -> AutoFixResult:
    """Generate an auto-fix patch using LLM."""
    gateway = get_llm_gateway(settings)

    # Get diagnosis data
    diagnosis = pipeline_run.diagnosis_report_json or {}
    error_type = diagnosis.get("error_type", "Unknown")
    possible_causes = diagnosis.get("possible_causes", [])
    suggested_fixes = diagnosis.get("suggested_fixes", [])

    # Get diff
    diff_text = "No diff available."
    if pipeline_run.repository_full_name and pipeline_run.commit_sha:
        owner, repo = pipeline_run.repository_full_name.split("/", 1)
        base_sha = pipeline_run.commit_sha[:7] + "0" * 33
        diff_data = await client.get_compare(
            pipeline_run.installation_id or 0,
            owner,
            repo,
            base_sha,
            pipeline_run.commit_sha,
        )
        diff_text = format_diff_for_llm(diff_data)

    messages = build_autofix_prompt(
        error_type=error_type,
        possible_causes=possible_causes,
        diff_text=diff_text,
        workflow_name=pipeline_run.workflow_name or "unknown",
        branch=pipeline_run.branch or "unknown",
        suggested_fixes=suggested_fixes,
    )

    response = await gateway.complete(
        agent=AgentType.AUTOFIX,
        messages=messages,
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    try:
        data = json.loads(response.content)
    except json.JSONDecodeError:
        return AutoFixResult(
            summary="Failed to parse LLM response",
            files=[],
            provider=response.provider.value,
            model=response.model,
            raw_response=response.content,
        )

    return AutoFixResult(
        summary=data.get("summary", "No summary provided"),
        files=data.get("files", []),
        provider=response.provider.value,
        model=response.model,
        raw_response=response.content,
    )


async def create_fix_branch(
    client: GitHubAppClient,
    installation_id: int,
    owner: str,
    repo: str,
    branch_name: str,
    base_sha: str,
) -> bool:
    """Create a new branch for the fix."""
    try:
        await client.create_ref(installation_id, owner, repo, branch_name, base_sha)
        return True
    except Exception:
        return False


async def apply_fix_files(
    client: GitHubAppClient,
    installation_id: int,
    owner: str,
    repo: str,
    files: list[dict[str, str]],
    branch: str,
    base_sha: str,
) -> str | None:
    """Apply fix files by creating blobs, trees, and commits."""
    try:
        # Get the base tree SHA from the base commit
        base_commit = await client.get_commit(installation_id, owner, repo, base_sha)
        base_tree_sha = base_commit.get("tree", {}).get("sha")
        if not base_tree_sha:
            raise GitHubAppError("Failed to get base tree SHA from commit")

        # Create blobs for each file
        file_entries = []
        for file in files:
            blob_result = await client.create_blob(
                installation_id, owner, repo, file["new_content"]
            )
            file_entries.append(
                {
                    "path": file["path"],
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_result["sha"],
                }
            )

        # Create new tree based on base tree (preserves all other files)
        tree_result = await client.create_tree(
            installation_id, owner, repo, file_entries, base_tree=base_tree_sha
        )
        tree_sha = tree_result["sha"]

        # Create commit
        commit_result = await client.create_commit(
            installation_id,
            owner,
            repo,
            f"PipelineIQ auto-fix: {files[0]['path'] if files else 'fix'}",
            tree_sha,
            [base_sha],
        )
        commit_sha = commit_result["sha"]

        # Update the branch reference (try update first, fall back to create)
        try:
            await client.update_ref(installation_id, owner, repo, branch, commit_sha)
        except GitHubAppError:
            # Branch might not exist yet, try to create it
            await client.create_ref(installation_id, owner, repo, branch, commit_sha)

        return commit_sha  # type: ignore[no-any-return]
    except Exception:
        return None


async def create_pull_request(
    client: GitHubAppClient,
    installation_id: int,
    owner: str,
    repo: str,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str,
) -> dict[str, Any] | None:
    """Create a pull request for the fix."""
    try:
        return await client.create_pull_request(
            installation_id, owner, repo, title, body, head_branch, base_branch
        )
    except Exception:
        return None


def build_pr_body(
    pipeline_run: PipelineRun,
    result: AutoFixResult,
    execution_id: str,
) -> str:
    """Build the PR description body."""
    diagnosis = pipeline_run.diagnosis_report_json or {}
    _ = pipeline_run.risk_report_json or {}

    return f"""## PipelineIQ Auto-Fix

**Execution ID**: {execution_id}
**Workflow**: {pipeline_run.workflow_name}
**Branch**: {pipeline_run.branch}
**Commit**: {pipeline_run.commit_sha}

### Diagnosis
- **Error Type**: {diagnosis.get("error_type", "Unknown")}
- **Possible Causes**: {", ".join(diagnosis.get("possible_causes", [])) or "None identified"}

### Fix Summary
{result.summary}

### Files Changed
{chr(10).join(f"- `{f['path']}`" for f in result.files)}

### Risk Assessment
- **Score**: {pipeline_run.risk_score or "N/A"} ({pipeline_run.risk_band or "unknown"})
- **Action**: {pipeline_run.autofix_mode or "N/A"}

---
*This PR was generated automatically by PipelineIQ. Please review carefully before merging.*"""


async def check_memory_for_auto_merge(
    settings: Settings,
    pipeline_run: PipelineRun,
) -> bool:
    """Check if similar failures have been approved for auto-merge."""
    if not pipeline_run.repository_full_name:
        return False

    error_signature = pipeline_run.error_summary or ""
    if not error_signature and pipeline_run.monitor_logs_excerpt:
        error_signature = "\n".join(pipeline_run.monitor_logs_excerpt[:3])

    memory = await AutoFixMemory.find_one(
        AutoFixMemory.repository_full_name == pipeline_run.repository_full_name,
        AutoFixMemory.error_signature == error_signature,
        AutoFixMemory.approved_for_auto_merge,
    )
    return memory is not None


async def record_autofix_memory(
    pipeline_run: PipelineRun,
    execution: AutoFixExecution,
    approved: bool,
) -> None:
    """Record auto-fix outcome in memory."""
    if not pipeline_run.repository_full_name:
        return

    error_signature = pipeline_run.error_summary or ""
    if not error_signature and pipeline_run.monitor_logs_excerpt:
        error_signature = "\n".join(pipeline_run.monitor_logs_excerpt[:3])

    existing = await AutoFixMemory.find_one(
        AutoFixMemory.repository_full_name == pipeline_run.repository_full_name,
        AutoFixMemory.error_signature == error_signature,
    )

    if existing:
        existing.approved_for_auto_merge = approved
        note = f"Auto-merge {'approved' if approved else 'rejected'} "
        note += f"from execution {execution.id}"
        existing.note = note
        existing.updated_at = datetime.now(UTC)
        await existing.save()
    else:
        note = f"Auto-merge {'approved' if approved else 'rejected'} "
        note += f"from execution {execution.id}"
        await AutoFixMemory(
            workspace_id=pipeline_run.workspace_id,
            repository_full_name=pipeline_run.repository_full_name,
            error_signature=error_signature,
            memory_type="autofix_outcome",
            approved_for_auto_merge=approved,
            note=note,
        ).insert()
