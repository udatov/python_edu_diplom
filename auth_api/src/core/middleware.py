from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from common.src.theatre.schemas.auth_schemas import UserInDB
import uuid


ANONYMOUS_USER_ID = str(uuid.uuid4())


class RoleBasedAccessControlMiddleware(BaseHTTPMiddleware):
    """
    Middleware для проверки прав доступа на основе ролей.
    Обрабатывает также анонимных пользователей.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get('X-Request-Id')
        if not request_id:
            request_id = str(uuid.uuid4())
            request.headers.__dict__["_list"].append((b'x-request-id', request_id.encode()))
        user = getattr(request.state, 'user', None)

        if not user:
            request.state.user = UserInDB(
                id=uuid.UUID(ANONYMOUS_USER_ID),
                login="anonymous",
                email="anonymous@xyz.net",
                first_name="Anonymous",
                last_name="User",
                roles=[],
            )

        response = await call_next(request)
        response.headers['X-Request-Id'] = request_id
        return response
