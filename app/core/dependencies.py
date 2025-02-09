from fastapi import Header, HTTPException, Depends
from app.core.config import settings

def verify_token(x_token: str = Header(...)) -> str:
    if x_token != settings.SECRET_KEY:
        raise HTTPException(
            status_code=403, detail="Invalid or missing token"
        )
    return x_token