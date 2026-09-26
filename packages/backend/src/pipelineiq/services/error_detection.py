"""Error detection: log parsing and failure classification for workflow runs."""

import re

# Patterns for detecting errors in logs
ERROR_PATTERNS = [
    r"(?i)error[:]",
    r"(?i)exception[:]",
    r"(?i)traceback",
    r"(?i)failed[:]",
    r"(?i)failure[:]",
    r"(?i)fatal[:]",
    r"(?i)panic[:]",
    r"(?i)assertion\s+error",
    r"(?i)segmentation\s+fault",
    r"(?i)out\s+of\s+memory",
    r"(?i)timeout",
    r"(?i)connection\s+refused",
    r"(?i)permission\s+denied",
    r"(?i)command\s+not\s+found",
    r"(?i)no\s+such\s+file",
    r"(?i)module\s+not\s+found",
    r"(?i)import\s+error",
    r"(?i)syntax\s+error",
    r"(?i)test.*failed",
    r"(?i)exit\s+code\s+[1-9]",
    r"FAILED",
    r"Error:",
    r"Exception:",
    r"FAIL",
]

# Patterns for extracting error context
CONTEXT_LINES = 5  # Lines before/after error to capture


def detect_failure(logs: str) -> tuple[str, str, list[str]]:
    """
    Detect failure in workflow logs.

    Returns:
        Tuple of (health_status, summary, excerpts)
        health_status: "healthy", "failed", or "unknown"
        summary: Human-readable summary
        excerpts: List of relevant log excerpts
    """
    if not logs or not logs.strip():
        return "unknown", "No logs available", []

    lines = logs.splitlines()
    error_matches = []

    for i, line in enumerate(lines):
        if any(re.search(pattern, line) for pattern in ERROR_PATTERNS):
            # Capture context around the error
            start = max(0, i - CONTEXT_LINES)
            end = min(len(lines), i + CONTEXT_LINES + 1)
            context = "\n".join(lines[start:end])
            error_matches.append(context)

    if not error_matches:
        return "healthy", "Workflow completed successfully", []

    # Deduplicate similar excerpts
    unique_excerpts = []
    seen = set()
    for excerpt in error_matches:
        # Simple deduplication based on first 200 chars
        key = excerpt[:200]
        if key not in seen:
            seen.add(key)
            unique_excerpts.append(excerpt)

    # Limit to top 5 excerpts
    excerpts = unique_excerpts[:5]

    # Generate summary
    summary = f"Detected {len(unique_excerpts)} error(s) in workflow logs"

    # Try to identify error type
    error_type = _classify_error("\n".join(excerpts))
    if error_type:
        summary = f"{error_type}: {summary}"

    return "failed", summary, excerpts


def _classify_error(log_text: str) -> str | None:
    """Classify the type of error from log text."""
    classifications = [
        (r"(?i)test.*fail", "Test Failure"),
        (r"(?i)assertion", "Assertion Error"),
        (r"(?i)timeout", "Timeout"),
        (r"(?i)out\s+of\s+memory|OOM", "Out of Memory"),
        (r"(?i)segmentation\s+fault|segfault", "Segmentation Fault"),
        (r"(?i)permission\s+denied", "Permission Denied"),
        (r"(?i)connection\s+refused|connection\s+timeout", "Connection Error"),
        (r"(?i)command\s+not\s+found", "Command Not Found"),
        (r"(?i)no\s+such\s+file|file\s+not\s+found", "File Not Found"),
        (r"(?i)module\s+not\s+found|import\s+error", "Import Error"),
        (r"(?i)syntax\s+error", "Syntax Error"),
        (r"(?i)dependency|package.*not\s+found", "Dependency Error"),
        (r"(?i)compilation|compile\s+error", "Compilation Error"),
        (r"(?i)lint|formatting", "Lint/Format Error"),
        (r"(?i)docker|container", "Container Error"),
        (r"(?i)kubernetes|k8s", "Kubernetes Error"),
    ]

    for pattern, classification in classifications:
        if re.search(pattern, log_text):
            return classification

    return None


def extract_error_signature(logs: str) -> str:
    """
    Extract a signature from error logs for pattern matching/memory.

    This creates a hashable representation of the error that can be used
    to identify similar failures across runs.
    """
    if not logs:
        return "unknown"

    # Find first error line
    lines = logs.splitlines()
    error_line = ""
    for line in lines:
        if any(re.search(pattern, line) for pattern in ERROR_PATTERNS):
            error_line = line.strip()
            break

    if not error_line:
        return "unknown"

    # Normalize: remove paths, line numbers, specific values
    normalized = re.sub(r"/[^\s]+", "<path>", error_line)
    normalized = re.sub(r"\b\d+\b", "<num>", normalized)
    normalized = re.sub(r"0x[0-9a-fA-F]+", "<hex>", normalized)
    normalized = re.sub(r"'[^']*'", "<str>", normalized)
    normalized = re.sub(r'"[^"]*"', "<str>", normalized)

    return normalized[:200]
