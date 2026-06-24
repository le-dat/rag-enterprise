import logging
from typing import Any
from qdrant_client.http import models as rest
from src.auth.jwt_handler import UserContext
from src.core.enums import Role

logger = logging.getLogger(__name__)

def build_qdrant_rbac_filter(user: UserContext) -> rest.Filter:
    """
    Builds a Qdrant query filter based on the user context (department and role).

    Rules:
    - User can only view documents belonging to their department.
    - If user is a 'staff', they can only view 'staff' level documents.
    - If user is a 'manager', they can view both 'staff' and 'manager' level documents.
    """
    conditions: list[Any] = []

    # 1. Department Filter
    conditions.append(
        rest.FieldCondition(
            key="department",
            match=rest.MatchValue(value=user.department)
        )
    )

    # 2. Role Filter (hierarchical)
    if user.role == Role.MANAGER.value:
        # Managers can access staff or manager documents
        conditions.append(
            rest.FieldCondition(
                key="role",
                match=rest.MatchAny(any=[Role.STAFF.value, Role.MANAGER.value])
            )
        )
    else:
        # Staff can ONLY access staff documents
        conditions.append(
            rest.FieldCondition(
                key="role",
                match=rest.MatchValue(value=Role.STAFF.value)
            )
        )

    logger.info(f"RBAC Filter built for department={user.department}, role={user.role}")
    return rest.Filter(must=conditions)
