"""FastAPI dependency injection utilities."""

from typing import Dict, Any
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from services.auth_service import get_current_user_claims
from models.user import User
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


async def get_db_user(
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI dependency: retrieves the database User model using Clerk credentials.
    Automatically creates the user record if it doesn't exist yet.
    """
    clerk_id = claims.get("sub")
    
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clerk token is missing sub (user_id) claim"
        )

    # Lookup user
    stmt = select(User).where(User.clerk_id == clerk_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        # Create user record on their first request
        email = claims.get("email") or claims.get("emails", [None])[0]
        full_name = claims.get("name") or f"{claims.get('given_name', '')} {claims.get('family_name', '')}".strip() or "Standard User"
        avatar_url = claims.get("picture") or claims.get("avatar")

        # If email is missing from claims (default Clerk token behavior), fetch from Clerk Backend API
        if not email and settings.clerk_secret_key:
            try:
                import httpx
                headers = {"Authorization": f"Bearer {settings.clerk_secret_key}"}
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"https://api.clerk.com/v1/users/{clerk_id}", headers=headers)
                    if resp.status_code == 200:
                        clerk_data = resp.json()
                        email_addresses = clerk_data.get("email_addresses", [])
                        if email_addresses:
                            email = email_addresses[0].get("email_address")
                        first_name = clerk_data.get("first_name") or ""
                        last_name = clerk_data.get("last_name") or ""
                        full_name = f"{first_name} {last_name}".strip() or full_name
                        avatar_url = clerk_data.get("image_url") or avatar_url
            except Exception as e:
                logger.error(f"Failed to fetch user profile from Clerk API: {e}")

        # If email is still missing, fallback to a safe database-compliant placeholder
        if not email:
            email = f"{clerk_id}@clerk-user.placeholder"

        user = User(
            clerk_id=clerk_id,
            email=email,
            full_name=full_name,
            avatar_url=avatar_url
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user
