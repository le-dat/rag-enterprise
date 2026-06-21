import logging
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from src.auth.jwt_handler import UserContext
from src.core.orchestrator import run_rag_pipeline

logger = logging.getLogger(__name__)


# ── Pydantic Schemas for Tool Inputs ──────────────────────────────────────────

class PolicyLookupInput(BaseModel):
    query: str = Field(..., description="The query to search in the policy database.")

class CreateLeaveRequestInput(BaseModel):
    employee_id: str = Field(..., description="The ID of the employee requesting leave.")
    start_date: str = Field(..., description="Start date of the leave in YYYY-MM-DD format.")
    end_date: str = Field(..., description="End date of the leave in YYYY-MM-DD format.")
    reason: str = Field(..., description="The reason for taking leave.")

class UpdateOpportunityInput(BaseModel):
    opp_id: str = Field(..., description="The opportunity ID (CRM identifier).")
    stage: str = Field(..., description="The new stage for the opportunity (e.g. Qualification, Proposal, Closed Won, Closed Lost).")
    next_step: str = Field(..., description="The defined next action step for this opportunity.")


# ── Tool Definitions ──────────────────────────────────────────────────────────

@tool("policy_lookup_tool", args_schema=PolicyLookupInput)
def policy_lookup_tool(query: str, config: RunnableConfig) -> str:
    """
    Search the company policies database (HR guidelines, leave policies, sales commissions, targets, etc.).
    Always use this tool when the user asks questions about corporate policies, regulations, or rules.
    """
    logger.info(f"policy_lookup_tool called with query={query!r}")
    configurable = config.get("configurable", {})
    user = configurable.get("user")
    if not user:
        return "Error: User context is missing or unauthenticated. Cannot query policies."

    # Extract services from config or load lazy fallbacks
    engine = configurable.get("search_engine")
    reranker = configurable.get("reranker")
    generator = configurable.get("generator")
    grounding_checker = configurable.get("grounding_checker")
    retrieval_rail = configurable.get("retrieval_rail")

    # Fallback instantiations
    if not engine:
        from src.retrieval.hybrid_search import HybridSearchEngine
        engine = HybridSearchEngine()
    if not reranker:
        from src.retrieval.reranker import CohereReranker
        reranker = CohereReranker()
    if not generator:
        from src.generation.generator import OpenAIGenerator
        generator = OpenAIGenerator()
    if not grounding_checker:
        from src.generation.grounding import GroundingChecker
        grounding_checker = GroundingChecker()
    if not retrieval_rail:
        from src.guardrails.retrieval_rail import RetrievalRail
        retrieval_rail = RetrievalRail()

    try:
        res = run_rag_pipeline(
            query=query,
            user=user,
            engine=engine,
            reranker=reranker,
            generator=generator,
            grounding_checker=grounding_checker,
            retrieval_rail=retrieval_rail,
        )
        return (
            f"Answer: {res['answer']}\n\n"
            f"[Grounding Status: {res['grounding'].get('grounded')}]"
        )
    except Exception as e:
        logger.error(f"Error in policy_lookup_tool: {e}")
        return f"Error retrieving policy details: {str(e)}"


@tool("create_leave_request_tool", args_schema=CreateLeaveRequestInput)
def create_leave_request_tool(
    employee_id: str, start_date: str, end_date: str, reason: str, config: RunnableConfig
) -> str:
    """
    Create a leave request in the HR system.
    Only HR department members are authorized to call this action tool.
    """
    logger.info(f"create_leave_request_tool called: employee_id={employee_id}, dates={start_date} to {end_date}")
    configurable = config.get("configurable", {})
    user: UserContext = configurable.get("user")
    
    if not user:
        return "Error: User context is missing. Cannot request leave."
        
    # Department validation (RBAC)
    if user.department.upper() != "HR":
        return f"Access Denied: User {user.user_id} (Department: {user.department}) is not authorized to create leave requests. This tool is restricted to HR department."

    # Perform action (Mock implementation)
    return (
        f"Success: Leave request created successfully in HR system.\n"
        f"Details:\n"
        f"- Employee: {employee_id}\n"
        f"- Period: {start_date} to {end_date}\n"
        f"- Reason: {reason}\n"
        f"- Created By: {user.user_id} (HR Manager/Staff)"
    )


@tool("update_crm_opportunity_tool", args_schema=UpdateOpportunityInput)
def update_crm_opportunity_tool(
    opp_id: str, stage: str, next_step: str, config: RunnableConfig
) -> str:
    """
    Update a CRM Sales opportunity stage and next steps.
    Only Sales department members are authorized to call this action tool.
    """
    logger.info(f"update_crm_opportunity_tool called: opp_id={opp_id}, stage={stage}")
    configurable = config.get("configurable", {})
    user: UserContext = configurable.get("user")
    
    if not user:
        return "Error: User context is missing. Cannot update CRM."
        
    # Department validation (RBAC)
    if user.department.upper() != "SALES":
        return f"Access Denied: User {user.user_id} (Department: {user.department}) is not authorized to update CRM opportunities. This tool is restricted to Sales department."

    # Perform action (Mock implementation)
    return (
        f"Success: CRM Opportunity {opp_id} updated successfully.\n"
        f"Details:\n"
        f"- New Stage: {stage}\n"
        f"- Next Step: {next_step}\n"
        f"- Updated By: {user.user_id} (Sales Agent)"
    )
