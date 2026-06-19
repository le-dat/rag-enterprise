import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.auth.jwt_handler import verify_token, UserContext

logger = logging.getLogger(__name__)

# Security scheme instance for Bearer Token
security_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
) -> UserContext:
    """
    FastAPI dependency that parses the Authorization header,
    verifies the Bearer JWT, and injects UserContext.
    Throws HTTP 401 on failure.
    """
    token = credentials.credentials
    user_context = verify_token(token)
    
    if not user_context:
        logger.warning("Failed authentication attempt: invalid or expired token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials. Please check token integrity or expiration.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    logger.info(f"Authenticated user {user_context.user_id} ({user_context.department}/{user_context.role})")
    return user_context
