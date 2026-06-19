from jose import jwt, JWTError
from pydantic import BaseModel, Field
from src.config import settings

class UserContext(BaseModel):
    user_id: str = Field(..., description="Unique identifier of the employee")
    role: str = Field(..., description="RBAC role level (e.g. manager, staff)")
    department: str = Field(..., description="RBAC department affiliation (e.g. HR, Sales)")

from datetime import datetime, timedelta, timezone
from typing import Optional

def generate_token(user_id: str, role: str, department: str) -> str:
    """
    Generate a signed JWT token with custom RBAC payload claims.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": user_id,
        "role": role.strip(),
        "department": department.strip(),
        "exp": expire
    }
    
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def verify_token(token: str) -> Optional[UserContext]:
    """
    Decode and validate a JWT Bearer token.
    Returns UserContext if valid, else None.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        department: str = payload.get("department")
        
        if not user_id or not role or not department:
            return None
            
        return UserContext(
            user_id=user_id,
            role=role,
            department=department
        )
    except JWTError:
        return None
