"""Authentication service for verifying Clerk JWTs and injecting current user."""

import httpx
from typing import Optional, Dict, Any
from jose import jwt, jwt as jose_jwt
from jose.exceptions import JWTError, ExpiredSignatureError
from fastapi import Request, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Security scheme
security_scheme = HTTPBearer(auto_error=False)


class ClerkAuthService:
    """Handles Clerk JWT validation using JWKS (JSON Web Key Sets)."""

    _jwks_cache: Optional[Dict[str, Any]] = None

    @classmethod
    async def get_jwks(cls) -> Dict[str, Any]:
        """Fetch the JSON Web Key Set from Clerk with caching."""
        if cls._jwks_cache:
            return cls._jwks_cache

        jwks_url = settings.clerk_jwks_url
        if not jwks_url or "your-clerk-domain" in jwks_url:
            # Fallback placeholder for dev
            logger.warning("CLERK_JWKS_URL is not set or is placeholder. Auth will be in mock mode for development.")
            return {"keys": []}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(jwks_url)
                response.raise_for_status()
                cls._jwks_cache = response.json()
                logger.info("Clerk JWKS loaded and cached successfully.")
                return cls._jwks_cache
        except Exception as e:
            logger.error(f"Failed to fetch Clerk JWKS: {e}")
            # Do not raise exception on startup, allowing dev fallback
            return {"keys": []}

    @classmethod
    async def verify_token(cls, token: str) -> Dict[str, Any]:
        """Verify the Clerk JWT and return decoded payload."""
        if (
            not settings.clerk_jwks_url 
            or "your-clerk-domain" in settings.clerk_jwks_url 
            or token == "mock_token_123456"
        ):
            # Mock mode for development
            logger.info("Verifying token in MOCK mode (placeholder/mock token).")
            return {
                "sub": "user_mock_123456",
                "email": "mockuser@example.com",
                "name": "Mock SDE Candidate"
            }

        jwks = await cls.get_jwks()
        
        try:
            # Decode the header to find the kid (key id)
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            if not kid:
                raise HTTPException(status_code=401, detail="Missing Key ID (kid) in token header")

            # Find matching key in JWKS
            rsa_key = {}
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    rsa_key = {
                        "kty": key.get("kty"),
                        "kid": key.get("kid"),
                        "use": key.get("use"),
                        "n": key.get("n"),
                        "e": key.get("e")
                    }
                    break

            if not rsa_key:
                raise HTTPException(
                    status_code=401,
                    detail=f"Invalid Key ID (kid) '{kid}' / signing key not found in JWKS keys: {[k.get('kid') for k in jwks.get('keys', [])]}"
                )

            # Verify signature & decodes payload
            # In Clerk JWT, 'azp' holds the frontend client/origin or publishable key, or we just check signature & issuer
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                options={"verify_aud": False}  # Clerk token audience is usually the frontend client
            )
            return payload

        except ExpiredSignatureError:
            logger.warning("Token signature has expired")
            raise HTTPException(status_code=401, detail="Token signature has expired")
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise HTTPException(status_code=401, detail=f"Could not validate credentials: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in token verification: {e}")
            raise HTTPException(status_code=500, detail=f"Internal authentication error: {str(e)}")


async def get_current_user_claims(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Dict[str, Any]:
    """FastAPI dependency: Extract and verify Clerk JWT claims from Bearer token."""
    if not credentials:
        # For development ease, if no auth is provided, default to mock in non-prod
        if settings.app_env == "development":
            return {
                "sub": "user_mock_123456",
                "email": "mockuser@example.com",
                "name": "Mock SDE Candidate",
                "avatar": "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=150"
            }
        raise HTTPException(
            status_code=401,
            detail=f"Bearer token is required. (env={settings.app_env}, debug={settings.app_debug})"
        )

    return await ClerkAuthService.verify_token(credentials.credentials)
