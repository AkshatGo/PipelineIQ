"""Diagnosis stage: LLM-based root cause analysis for workflow failures."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pipelineiq.config import Settings
from pipelineiq.models import PipelineRun
from pipelineiq.services.github_app import GitHubAppClient
from pipelineiq.services.llm_gateway import AgentType, get_llm_gateway

DIAGNOSIS_SYSTEM_PROMPT = """You are an expert CI/CD failure analyst. Analyze the provided workflow failure logs and git diff to determine:

1. **error_type**: The category of error (e.g., "Test Failure", "Dependency Error", "Compilation Error", "Timeout", "Out of Memory", "Configuration Error", "Infrastructure Error")
2. **possible_causes**: List of likely root causes, ordered by probability
3. **latest_working_change**: Description of the most recent change that could have introduced the failure (from the git diff)
4. **suggested_fixes**: List of concrete, minimal fix suggestions

Output must be valid JSON matching the schema below. Be concise and precise."""


DIAGNOSIS_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "error_type": {"type": "string"},
        "possible_causes": {"type": "array", "items": {"type": "string"}},
        "latest_working_change": {"type": "string"},
        "suggested_fixes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["error_type", "possible_causes", "latest_working_change", "suggested_fixes"],
}


@dataclass
class DiagnosisResult:
    """Structured diagnosis result."""

    error_type: str
    possible_causes: list[str]
    latest_working_change: str
    suggested_fixes: list[str]
    provider: str
    model: str
    raw_response: str


async def fetch_workflow_diff(
    client: GitHubAppClient,
    installation_id: int,
    owner: str,
    repo: str,
    base_sha: str,
    head_sha: str,
) -> dict[str, Any] | None:
    """Fetch the git diff between base and head commits."""
    try:
        compare = await client.get_compare(installation_id, owner, repo, base_sha, head_sha)
        return compare
    except Exception:
        return None


def format_diff_for_llm(diff_data: dict[str, Any] | None) -> str:
    """Format GitHub compare API response for LLM consumption."""
    if not diff_data:
        return "No diff data available."

    files = diff_data.get("files", [])
    if not files:
        return "No file changes in diff."

    parts = []
    for file in files[:10]:  # Limit to 10 files
        filename = file.get("filename", "unknown")
        status = file.get("status", "modified")
        patch = file.get("patch", "")
        parts.append(f"=== {filename} ({status}) ===")
        if patch:
            # Truncate patch to avoid token limits
            parts.append(patch[:3000])
        else:
            additions = file.get("additions", 0)
            deletions = file.get("deletions", 0)
            parts.append(f"  +{additions} -{deletions} (binary or large file)")

    return "\n".join(parts)


def build_diagnosis_prompt(
    error_logs: str,
    diff_text: str,
    workflow_name: str,
    branch: str,
) -> list[dict[str, str]]:
    """Build the diagnosis prompt for the LLM."""
    user_prompt = f"""Analyze this CI/CD failure:

**Workflow**: {workflow_name}
**Branch**: {branch}

**Error Logs**:
```
{error_logs[:8000]}
```

**Git Diff (base -> head)**:
```
{diff_text[:8000]}
```

Provide diagnosis as JSON."""

    return [
        {"role": "system", "content": DIAGNOSIS_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


async def run_diagnosis(
    pipeline_run: PipelineRun,
    settings: Settings,
    client: GitHubAppClient,
) -> DiagnosisResult:
    """Run the diagnosis stage for a pipeline run."""
    gateway = get_llm_gateway(settings)

    # Get error logs from monitor stage
    error_logs = "\n".join(pipeline_run.monitor_logs_excerpt) if pipeline_run.monitor_logs_excerpt else ""
    if not error_logs and pipeline_run.monitor_summary:
        error_logs = pipeline_run.monitor_summary

    # Fetch diff
    diff_text = "No diff available."
    if pipeline_run.repository_full_name and pipeline_run.commit_sha:
        owner, repo = pipeline_run.repository_full_name.split("/", 1)
        # We need the base commit - for now use a reasonable default
        # In production, this would come from the workflow run data
        base_sha = pipeline_run.commit_sha[:7] + "0" * 33  # Placeholder
        diff_data = await fetch_workflow_diff(
            client,
            pipeline_run.installation_id or 0,
            owner,
            repo,
            base_sha,
            pipeline_run.commit_sha,
        )
        diff_text = format_diff_for_llm(diff_data)

    messages = build_diagnosis_prompt(
        error_logs=error_logs,
        diff_text=diff_text,
        workflow_name=pipeline_run.workflow_name or "unknown",
        branch=pipeline_run.branch or "unknown",
    )

    response = await gateway.complete(
        agent=AgentType.DIAGNOSIS,
        messages=messages,
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    # Parse JSON response
    try:
        data = json.loads(response.content)
    except json.JSONDecodeError:
        # Fallback: return structured error
        return DiagnosisResult(
            error_type="Unknown",
            possible_causes=["Failed to parse LLM response"],
            latest_working_change="Unknown",
            suggested_fixes=["Review logs manually"],
            provider=response.provider.value,
            model=response.model,
            raw_response=response.content,
        )

    return DiagnosisResult(
        error_type=data.get("error_type", "Unknown"),
        possible_causes=data.get("possible_causes", []),
        latest_working_change=data.get("latest_working_change", "Unknown"),
        suggested_fixes=data.get("suggested_fixes", []),
        provider=response.provider.value,
        model=response.model,
        raw_response=response.content,
    )


def apply_diagnosis_to_pipeline_run(pipeline_run: PipelineRun, result: DiagnosisResult) -> None:
    """Apply diagnosis result to pipeline run document."""
    pipeline_run.diagnosis_report = (
        f"Error Type: {result.error_type}\n"
        f"Possible Causes:\n" + "\n".join(f"  - {c}" for c in result.possible_causes) + "\n"
        f"Latest Working Change: {result.latest_working_change}\n"
        f"Suggested Fixes:\n" + "\n".join(f"  - {f}" for f in result.suggested_fixes)
    )
    pipeline_run.diagnosis_report_json = {
        "error_type": result.error_type,
        "possible_causes": result.possible_causes,
        "latest_working_change": result.latest_working_change,
        "suggested_fixes": result.suggested_fixes,
    }
    pipeline_run.diagnosis_provider = result.provider
    pipeline_run.diagnosis_model = result.model