"""Supabase JWT verification (JWKS ES256/RS256 and legacy HS256) and auth dependencies."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt import PyJWKClient

from backend.app.core.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)

# Strict algorithm allowlists separated by key type to prevent key-confusion attacks.
ASYMMETRIC_JWKS_ALGORITHMS = ["ES256", "RS256"]
SYMMETRIC_LEGACY_ALGORITHMS = ["HS256"]


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: Optional[str] = None
    role: str = "authenticated"


@lru_cache(maxsize=8)
def _get_jwk_client(jwks_url: str) -> PyJWKClient:
    """Return a cached PyJWKClient for a Supabase project's JWKS endpoint."""
    return PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600, timeout=10)


def _decode_with_jwks(token: str, supabase_url: str) -> dict:
    """Verify an asymmetric Supabase JWT (ES256/RS256) against the project's JWKS endpoint."""
    base_url = supabase_url.rstrip("/")
    jwks_url = f"{base_url}/auth/v1/.well-known/jwks.json"
    expected_issuer = f"{base_url}/auth/v1"

    jwk_client = _get_jwk_client(jwks_url)
    try:
        signing_key = jwk_client.get_signing_key_from_jwt(token)
    except jwt.PyJWKClientConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to reach Supabase JWKS endpoint for token verification.",
        ) from exc
    except jwt.PyJWKClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to find a matching signing key for authentication token.",
        ) from exc

    return jwt.decode(
        token,
        signing_key.key,
        algorithms=ASYMMETRIC_JWKS_ALGORITHMS,
        issuer=expected_issuer,
        audience="authenticated",
        options={
            "require": ["exp", "sub"],
            "verify_signature": True,
            "verify_exp": True,
            "verify_iss": True,
            "verify_aud": True,
        },
    )


def _decode_with_hs256(token: str, jwt_secret: str, supabase_url: str = "") -> dict:
    """Verify a legacy HS256 Supabase JWT using the server-side SUPABASE_JWT_SECRET."""
    decode_kwargs: dict = {
        "algorithms": SYMMETRIC_LEGACY_ALGORITHMS,
        "options": {
            "require": ["sub"],
            "verify_signature": True,
            "verify_exp": True,
            "verify_iss": bool(supabase_url),
            "verify_aud": False,
        },
    }
    if supabase_url:
        decode_kwargs["issuer"] = f"{supabase_url.rstrip('/')}/auth/v1"

    payload = jwt.decode(token, jwt_secret, **decode_kwargs)
    if "aud" in payload and payload["aud"] != "authenticated":
        raise jwt.InvalidAudienceError("Invalid token audience.")
    return payload


def verify_supabase_jwt(
    token: str,
    jwt_secret: str = "",
    supabase_url: str = "",
) -> AuthenticatedUser:
    """Verify a Supabase JWT via JWKS (ES256/RS256) or legacy HS256 secret."""
    if not jwt_secret and not supabase_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured (missing SUPABASE_URL and SUPABASE_JWT_SECRET).",
        )

    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed authentication token.",
        ) from exc

    has_kid = bool(unverified_header.get("kid"))

    try:
        if supabase_url and (has_kid or not jwt_secret):
            payload = _decode_with_jwks(token, supabase_url)
        elif jwt_secret:
            payload = _decode_with_hs256(token, jwt_secret, supabase_url=supabase_url)
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication is not configured (missing SUPABASE_URL or SUPABASE_JWT_SECRET).",
            )
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
        ) from exc
    except jwt.InvalidAlgorithmError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unsupported JWT signing algorithm.",
        ) from exc
    except jwt.InvalidSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token signature.",
        ) from exc
    except (jwt.InvalidIssuerError, jwt.InvalidAudienceError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token claims.",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        ) from exc

    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing subject (sub).",
        )

    return AuthenticatedUser(
        id=sub,
        email=payload.get("email"),
        role=payload.get("role", "authenticated"),
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> AuthenticatedUser:
    """Require a valid Supabase Bearer JWT for protected endpoints."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    settings = get_settings()
    return verify_supabase_jwt(
        credentials.credentials,
        jwt_secret=settings.supabase_jwt_secret,
        supabase_url=settings.supabase_url,
    )


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[AuthenticatedUser]:
    """Validate Bearer JWT if provided; return None when anonymous."""
    if credentials is None or not credentials.credentials:
        return None
    settings = get_settings()
    return verify_supabase_jwt(
        credentials.credentials,
        jwt_secret=settings.supabase_jwt_secret,
        supabase_url=settings.supabase_url,
    )
