import uuid
import logging
from typing import Literal
from fastapi import APIRouter
from pydantic import BaseModel, Field
from src.auth.jwt_handler import generate_token

logger = logging.getLogger(__name__)
router = APIRouter()

class TokenRequest(BaseModel):
    role: Literal["manager", "staff"] = Field(description="User RBAC Role level")
    department: Literal["HR", "Sales"] = Field(description="User RBAC Department")
    user_id: str = ""

@router.post("/token", summary="Generate a signed JWT token with RBAC claims")
def get_token(body: TokenRequest):
    """
    Generate mock JWT token for frontend role-selection testing.
    """
    u_id = body.user_id if body.user_id else f"emp_{str(uuid.uuid4())[:8]}"
    token = generate_token(user_id=u_id, role=body.role, department=body.department)
    logger.info(f"API token generated: user_id={u_id}, dept={body.department}, role={body.role}")
    return {"token": token, "user_id": u_id}
