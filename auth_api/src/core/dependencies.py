from functools import wraps
from logging import getLogger
from typing import Callable

from fastapi import Depends, HTTPException, status

from common.src.theatre.schemas.auth_schemas import UserInDB
from auth_api.src.services.access import AccessControlService, get_access_control_service
from typing import Annotated

from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError

from common.src.theatre.core.exception_handler import (
    fast_api_http_error_handler,
    filter_exception_decorator,
    get_auth_error,
)
from auth_api.src.services.auth import (
    AuthenticationService,
    get_authentication_service,
)

logger = getLogger(__name__)

""" 
Аутентификация по схеме OAuth2 (тип токена: Bearer).

Заголовок авторизации: { 'Authorization': 'Bearer <encoded_token>'}.

Доступ к авторизованным путям:
- проверка пары токенов (Access, Refresh) через get_current_user;
- при необходимости обновление пары токенов (Access, Refresh) после пройденной проверки.

См  пример @link https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/#oauth2passwordrequestform
"""

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='v1/auth/login')


@filter_exception_decorator(
    filter_error_handler=fast_api_http_error_handler,
    err_prefix_msg='Failed to authorize the user',
    err_logger=logger,
)
async def get_current_user(
    encoded_token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: AuthenticationService = Depends(get_authentication_service),
) -> UserInDB:
    """
    Вызываем на старте авторизованных запросов.
    Прежде, чем вернуть dto текущего пользователя, проведем проверку токенов.
    Проверка AccessToken при обращении к закрытым URL идет по следующим шагам:
    - декодируем токен: в случае ошибки вызываем InvalidTokenError
    - ищем пользователя: если не найден, вызываем HTTP Exception Code = 401
    - проверяем наличие RefreshToken: если не найден, вызываем HTTP Exception Code = 401
    - если проверка прошла успешно, возвращаем dto пользователя UserInDB

    Примечание: любой запрос авторизации должен начинаться с данного метода и завершаться продлением времени жизни Refresh token,
    перевыпуском Access Token.
    """
    try:
        return await auth_service.get_current_user(encoded_token=encoded_token)
    except InvalidTokenError:
        raise get_auth_error()


def requires_permission(permission_name: str):
    """
    Декоратор для проверки наличия права у пользователя.

    - permission_name: Название требуемого права
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(
            current_user: UserInDB = Depends(get_current_user),
            access_control_service: AccessControlService = Depends(get_access_control_service),
            *args,
            **kwargs,
        ):
            has_permission = await access_control_service.check_user_has_permission(
                user_id=str(current_user.id), permission_name=permission_name
            )

            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f'Недостаточно прав для выполнения операции. Требуется: {permission_name}',
                )

            return await func(current_user=current_user, *args, **kwargs)

        return wrapper

    return decorator
