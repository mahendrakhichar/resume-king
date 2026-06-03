"""FastAPI dependency injection utilities."""

from typing import Dict, Any
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from services.auth_service import get_current_user_claims
from models.user import User

async def get_db_user(
    claims: Dict[str, Any] = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI dependency: retrieves the database User model using Clerk credentials.
    Automatically creates the user record if it doesn't exist yet.
    """
    clerk_id = claims.get("sub")
    email = claims.get("email") or claims.get("emails", [None])[0]  # Clerk claims structure variation
    
    if not clerk_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clerk token is missing sub or email claims"
        )

    # Lookup user
    stmt = select(User).where(User.clerk_id == clerk_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        # Create user record on their first request
        full_name = claims.get("name") or f"{claims.get('given_name', '')} {claims.get('family_name', '')}".strip() or "Standard User"
        avatar_url = claims.get("picture") or claims.get("avatar")
        
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
