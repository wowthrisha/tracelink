from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from jose import jwt, JWTError, ExpiredSignatureError
from app.config import settings


class TokenExpiredError(Exception):
    """Raised when a JWT token has expired."""


class TokenInvalidError(Exception):
    """Raised when a JWT token is malformed or has an invalid signature."""


def encode_token(
    payload: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    data = payload.copy()
    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
        data["exp"] = expire
    return jwt.encode(data, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except ExpiredSignatureError as e:
        raise TokenExpiredError("Token has expired") from e
    except JWTError as e:
        raise TokenInvalidError("Token is invalid") from e
