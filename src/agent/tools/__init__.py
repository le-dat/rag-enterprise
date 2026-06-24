"""
Agent tools package.

To register a new tool:
  1. Create tools/<domain>.py with a @tool-decorated function
  2. Import it here and add to __all__
"""
from src.agent.tools.policy import policy_lookup_tool
from src.agent.tools.hr import create_leave_request_tool
from src.agent.tools.crm import update_crm_opportunity_tool

__all__ = [
    "policy_lookup_tool",
    "create_leave_request_tool",
    "update_crm_opportunity_tool",
]
