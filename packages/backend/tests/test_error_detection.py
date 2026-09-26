"""Tests for error_detection service."""

from pipelineiq.services.error_detection import (
    detect_failure,
    extract_error_signature,
)


def test_detect_failure_healthy_logs() -> None:
    logs = """
    Starting workflow...
    Running tests...
    All tests passed!
    Build successful.
    """
    status, summary, excerpts = detect_failure(logs)
    assert status == "healthy"
    assert "successfully" in summary.lower()
    assert excerpts == []


def test_detect_failure_with_test_failure() -> None:
    logs = """
    Running tests...
    test_user_login FAILED
    AssertionError: Expected True, got False
    test_user_logout PASSED
    """
    status, summary, excerpts = detect_failure(logs)
    assert status == "failed"
    assert "error" in summary.lower()
    assert len(excerpts) > 0
    assert any("FAILED" in e for e in excerpts)


def test_detect_failure_with_traceback() -> None:
    logs = """
    Traceback (most recent call last):
      File "test.py", line 10, in test_something
        raise ValueError("Invalid input")
    ValueError: Invalid input
    """
    status, summary, excerpts = detect_failure(logs)
    assert status == "failed"
    assert any("traceback" in e.lower() or "valueerror" in e.lower() for e in excerpts)


def test_detect_failure_with_timeout() -> None:
    logs = """
    Running long test...
    Timeout: Test exceeded 300 seconds
    """
    status, summary, excerpts = detect_failure(logs)
    assert status == "failed"
    assert "timeout" in summary.lower()


def test_detect_failure_with_oom() -> None:
    logs = """
    Running memory intensive test...
    Out of memory: Killed process
    """
    status, summary, excerpts = detect_failure(logs)
    assert status == "failed"
    assert "memory" in summary.lower()


def test_detect_failure_empty_logs() -> None:
    status, summary, excerpts = detect_failure("")
    assert status == "unknown"
    assert "no logs" in summary.lower()


def test_detect_failure_whitespace_only() -> None:
    status, summary, excerpts = detect_failure("   \n\n  \t  ")
    assert status == "unknown"


def test_extract_error_signature_basic() -> None:
    logs = "Error: test_user_login FAILED at line 42"
    signature = extract_error_signature(logs)
    assert "FAILED" in signature
    assert "<num>" in signature  # Line number normalized


def test_extract_error_signature_with_path() -> None:
    logs = "Error: File \"/home/user/project/src/main.py\", line 10, in main"
    signature = extract_error_signature(logs)
    assert "<path>" in signature


def test_extract_error_signature_with_hex() -> None:
    logs = "Segmentation fault at 0x7f8a3c001000"
    signature = extract_error_signature(logs)
    assert "<hex>" in signature


def test_extract_error_signature_with_quotes() -> None:
    logs = "ValueError: Invalid value 'test_value' at position 5"
    signature = extract_error_signature(logs)
    assert "<str>" in signature
    assert "<num>" in signature


def test_extract_error_signature_no_errors() -> None:
    logs = "All tests passed successfully"
    signature = extract_error_signature(logs)
    assert signature == "unknown"