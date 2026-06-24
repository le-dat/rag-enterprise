"""
Tool response schema helpers for the agent layer.

LLM tool output is pure internal reasoning — NOT HTTP responses.
Use these helpers to ensure a consistent structure that the LLM
can reliably parse and reason about.

Status values:
  "ok"     — tool executed successfully
  "error"  — tool execution failed (runtime exception)
  "denied" — access control rejected the call (rbac_guard)
"""
import json


def tool_ok(data: dict) -> str:
    """Wrap a successful tool result."""
    return json.dumps({"status": "ok", **data})


def tool_fail(code: str, detail: str) -> str:
    """Wrap a tool execution failure (exceptions, downstream errors)."""
    return json.dumps({"status": "error", "code": code, "detail": detail})


def tool_denied(user_id: str, department: str, required: list[str]) -> str:
    """Wrap an RBAC access denial with structured context for LLM reasoning."""
    return json.dumps({
        "status": "denied",
        "code": "ACCESS_DENIED",
        "detail": (
            f"User {user_id} (Department: {department}) is not authorized. "
            f"Required departments: {required}."
        ),
    })
