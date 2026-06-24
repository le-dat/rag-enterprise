"""
HR tool — create leave requests in the HR system.
Restricted to HR department members only.
"""
import logging

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from src.agent.middleware import rbac_guard
from src.agent.schemas import tool_ok, tool_fail

logger = logging.getLogger(__name__)


class CreateLeaveRequestInput(BaseModel):
    employee_id: str = Field(..., description="The ID of the employee requesting leave.")
    start_date: str = Field(..., description="Start date of the leave in YYYY-MM-DD format.")
    end_date: str = Field(..., description="End date of the leave in YYYY-MM-DD format.")
    reason: str = Field(..., description="The reason for taking leave.")


@tool("create_leave_request_tool", args_schema=CreateLeaveRequestInput)
@rbac_guard(allowed_departments=["HR"])
def create_leave_request_tool(
    employee_id: str,
    start_date: str,
    end_date: str,
    reason: str,
    config: RunnableConfig,
) -> str:
    """
    Create a leave request in the HR system.
    Only HR department members are authorized to call this action tool.
    """
    logger.info(
        "create_leave_request_tool called: employee_id=%s, dates=%s to %s",
        employee_id, start_date, end_date,
    )
    try:
        user = config.get("configurable", {}).get("user")
        assert user is not None
        return tool_ok({
            "message": "Leave request created successfully in HR system.",
            "details": {
                "employee_id": employee_id,
                "start_date": start_date,
                "end_date": end_date,
                "reason": reason,
                "created_by": user.user_id,
            },
        })
    except Exception as exc:
        logger.error("Error in create_leave_request_tool: %s", exc)
        return tool_fail(
            code="HR_SYSTEM_ERROR",
            detail=f"Failed to create leave request: {exc}",
        )
