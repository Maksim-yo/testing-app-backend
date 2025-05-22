from fastapi import Depends, HTTPException, Header
from jose import jwt, JWTError
from pydantic import BaseModel
from typing import Optional
import httpx
from auth import jwks_cache, CLERK_ISSUER

class UserData(BaseModel):
    user_id: str
    full_name: Optional[str] = None
    email: Optional[str] = None

async def get_current_user(authorization: str = Header(...)) -> UserData:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    
    token = authorization.split(" ")[1]
    
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        keys = jwks_cache.get("keys")

        if not keys:
            raise HTTPException(status_code=503, detail="JWKS not available")

        key = next((k for k in keys if k["kid"] == kid), None)
        if not key:
            raise HTTPException(status_code=401, detail="Public key not found.")

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=CLERK_ISSUER,
            options={"verify_aud": False},
        )

        return UserData(
            user_id=payload.get("id"),
            full_name=payload.get("name"),
            email=payload.get("email")
        )

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token validation error: {str(e)}")