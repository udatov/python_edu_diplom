import jwt
from fastapi import HTTPException, Cookie, status

from config import settings

def get_current_user_id(token: str = Cookie(default=None)) -> str:
    if not token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing token")
    try:
        payload = jwt.decode(token, settings.auth_public_key, algorithms=[settings.auth_algorithm])
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError()
        return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
