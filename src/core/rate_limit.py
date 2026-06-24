"""
Shared rate limiter instance.

Kept in a dedicated module so both main.py (app setup) and route modules
(decorator usage) can import from the same object without circular imports.

Key strategy: JWT 'sub' claim → per-user limiting.
Fallback: client IP (for unauthenticated or malformed tokens).

For multi-worker deployments, swap the default in-memory storage with a
Redis backend:
    limiter = Limiter(key_func=..., storage_uri="redis://localhost:6379")
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _rate_limit_key(request: Request) -> str:
    """Use JWT 'sub' claim as rate-limit key; fall back to remote IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            from jose import jwt as jose_jwt
            payload = jose_jwt.get_unverified_claims(auth.split(" ", 1)[1])
            sub = payload.get("sub")
            if sub:
                return sub
        except Exception:
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key)
