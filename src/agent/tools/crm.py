"""
CRM tool — update sales opportunity stage and next steps.
Restricted to Sales department members only.
"""
import logging

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from src.agent.middleware import rbac_guard
from src.agent.schemas import tool_ok, tool_fail

logger = logging.getLogger(__name__)


class UpdateOpportunityInput(BaseModel):
    opp_id: str = Field(..., description="The opportunity ID (CRM identifier).")
    stage: str = Field(
        ...,
        description="The new stage (e.g. Qualification, Proposal, Closed Won, Closed Lost).",
    )
    next_step: str = Field(..., description="The defined next action step for this opportunity.")


@tool("update_crm_opportunity_tool", args_schema=UpdateOpportunityInput)
@rbac_guard(allowed_departments=["SALES"])
def update_crm_opportunity_tool(
    opp_id: str,
    stage: str,
    next_step: str,
    config: RunnableConfig,
) -> str:
    """
    Update a CRM Sales opportunity stage and next steps.
    Only Sales department members are authorized to call this action tool.
    """
    logger.info("update_crm_opportunity_tool called: opp_id=%s, stage=%s", opp_id, stage)
    try:
        user = config.get("configurable", {}).get("user")
        assert user is not None
        return tool_ok({
            "message": f"CRM Opportunity {opp_id} updated successfully.",
            "details": {
                "opp_id": opp_id,
                "stage": stage,
                "next_step": next_step,
                "updated_by": user.user_id,
            },
        })
    except Exception as exc:
        logger.error("Error in update_crm_opportunity_tool: %s", exc)
        return tool_fail(
            code="CRM_SYSTEM_ERROR",
            detail=f"Failed to update CRM opportunity: {exc}",
        )
