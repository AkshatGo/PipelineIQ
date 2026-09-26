from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import uuid4

from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError

from pipelineiq.config import Settings


class TokenKind(StrEnum):
    SESSION = "session"
    OAUTH_STATE = "oauth_state"


class TokenClaims(BaseModel):
    sub: str
    kind: TokenKind
    iat: datetime
    exp: datetime
    jti: str


class TokenValidationError(ValueError):
    pass


def create_token(
    *,
    subject: str,
    kind: TokenKind,
    lifetime: timedelta,
    settings: Settings,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "kind": kind.value,
        "iat": now,
        "exp": now + lifetime,
        "jti": str(uuid4()),
        "iss": "pipelineiq",
        "aud": "pipelineiq-web",
    }
    return str(jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM))


def decode_token(token: str, *, expected_kind: TokenKind, settings: Settings) -> TokenClaims:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            issuer="pipelineiq",
            audience="pipelineiq-web",
        )
        claims = TokenClaims.model_validate(payload)
    except (JWTError, ValidationError, ValueError, TypeError) as exc:
        raise TokenValidationError("Token is invalid or expired") from exc
    if claims.kind is not expected_kind:
        raise TokenValidationError("Token has the wrong purpose")
    return claims


def create_session_token(user_id: str, settings: Settings) -> str:
    return create_token(
        subject=user_id,
        kind=TokenKind.SESSION,
        lifetime=timedelta(days=settings.SESSION_EXPIRY_DAYS),
        settings=settings,
    )


def create_oauth_state(settings: Settings) -> str:
    return create_token(
        subject=str(uuid4()),
        kind=TokenKind.OAUTH_STATE,
        lifetime=timedelta(minutes=10),
        settings=settings,
    )
