from logging import getLogger
from typing import Annotated, Any, Dict, List

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_limiter.depends import RateLimiter

from auth_api.src.core.dependencies import get_current_user, oauth2_scheme, requires_permission
from auth_api.src.core.config import G_RATE_LIMIT_SETTINGS, G_VK_OAUTH, G_YANDEX_OAUTH
from common.src.theatre.core.exception_handler import (
    fast_api_http_error_handler,
    filter_exception_decorator,
    get_auth_error,
)
from auth_api.src.core.sso.vk import VKSSO
from auth_api.src.core.sso.yandex import YandexSSO
from common.src.theatre.schemas.auth_schemas import (
    HttpToken,
    LoginHistoryItemDTO,
    PatchFormData,
    RedirectLogin,
    RegisterFormData,
    SSOUserData,
    UserCreate,
    UserInDB,
)
from auth_api.src.services.auth import (
    AuthenticationService,
    LoginHistoryService,
    get_authentication_service,
    get_loginhistory_service,
)
from common.src.theatre.schemas.model_filters import UserFilter

auth_router = APIRouter(
    prefix='',
    tags=['authorization'],
    responses={404: {'description': 'Not Found'}},
)

sso_router = APIRouter(
    prefix='',
    tags=['social-auth'],
    responses={404: {'description': 'Not Found'}},
)

yandex_sso = YandexSSO(
    client_id=G_YANDEX_OAUTH.client_id,
    client_secret=G_YANDEX_OAUTH.client_secret,
    redirect_uri=G_YANDEX_OAUTH.redirect_uri,
    allow_insecure_http=True,
)

vk_sso = VKSSO(
    client_id=G_VK_OAUTH.client_id,
    client_secret=G_VK_OAUTH.client_secret,
    redirect_uri=G_VK_OAUTH.redirect_uri,
)

logger = getLogger(__name__)


def get_authorization_token_response(http_token: HttpToken, content: Any) -> JSONResponse:
    json_compatible_item_data = jsonable_encoder(content)
    return JSONResponse(content=json_compatible_item_data, headers={'Authorization': http_token.authorization()})


AuthenticationServiceDeps = Annotated[AuthenticationService, Depends(get_authentication_service)]


@auth_router.post(
    '/register',
    response_model=UserInDB,
    summary='Регистрация',
    description='Регистрирует пользователя по переданным данным',
    dependencies=[Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.registration, seconds=G_RATE_LIMIT_SETTINGS.window))],
)
@filter_exception_decorator(
    filter_error_handler=fast_api_http_error_handler,
    err_prefix_msg='Failed to register the user',
    err_logger=logger,
)
async def user_register(
    form_data: Annotated[RegisterFormData, Form()],
    auth_service: AuthenticationService = Depends(get_authentication_service),
) -> UserInDB:
    """
    Регистрирует пользователя по переданным данным

    - login: Логин пользователя (обязательное поле)
    - email: Email пользователя (обязательное поле)
    - password: Пароль пользователя
    - first_name: Имя пользователя
    - last_name: Фамилия пользователя
    """

    new_user_dto: UserInDB = await auth_service.register(new_user_dto=UserCreate.model_validate(form_data))
    if not new_user_dto:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Could not create new user: {new_user_dto}'
        )
    return new_user_dto


@auth_router.post(
    '/login',
    response_model=HttpToken,
    summary='Вход',
    description='Возвращает токены для входа и повторного входа',
    dependencies=[Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.login, seconds=G_RATE_LIMIT_SETTINGS.window))],
)
@filter_exception_decorator(
    filter_error_handler=fast_api_http_error_handler,
    err_prefix_msg='Failed to login the user',
    err_logger=logger,
)
async def user_login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    auth_service: AuthenticationService = Depends(get_authentication_service),
    loginhistory_service: LoginHistoryService = Depends(get_loginhistory_service),
) -> HttpToken:
    """
    Аутентифицирует пользователя и возвращает Access токен.
    """
    return await auth_service.authorize(
        login=form_data.username,
        password=form_data.password,
        request=request,
        loginhistory_service=loginhistory_service,
    )


@auth_router.post(
    '/login_with_redirect',
    response_class=RedirectResponse,
    summary='Вход с перенаправлением',
    description='Записывает токен в session cookies и перенаправлет запрос',
    dependencies=[Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.login, seconds=G_RATE_LIMIT_SETTINGS.window))],
)
@filter_exception_decorator(
    filter_error_handler=fast_api_http_error_handler,
    err_prefix_msg='Failed to login the user',
    err_logger=logger,
)
async def user_login_with_redirect(
    redirect_login: RedirectLogin,
    request: Request,
    auth_service: AuthenticationService = Depends(get_authentication_service),
    loginhistory_service: LoginHistoryService = Depends(get_loginhistory_service),
) -> HttpToken:
    """
    Аутентифицирует пользователя, записывает токен в session cookies и перенаправляет на redirect_url.
    """
    http_token: HttpToken = await auth_service.authorize(
        login=redirect_login.username,
        password=redirect_login.password,
        request=request,
        loginhistory_service=loginhistory_service,
    )
    # Используем cookies для записи HttpToken токена, далее на клиенте делаем проверку cookies и извлекаем инфо из токена
    redirect_response: RedirectResponse = RedirectResponse(
        url=redirect_login.redirect_url, status_code=redirect_login.redirect_code
    )
    redirect_response.set_cookie(key='HttpToken', value=http_token.model_dump_json())
    return redirect_response


@auth_router.get(
    '/refresh',
    response_model=HttpToken,
    summary='Обновление токена',
    description='Возвращает обновленный Access токен.',
    dependencies=[Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.refresh, seconds=G_RATE_LIMIT_SETTINGS.window))],
)
@filter_exception_decorator(
    filter_error_handler=fast_api_http_error_handler,
    err_prefix_msg='Failed to refresh the user token',
    err_logger=logger,
)
async def user_refresh(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    auth_service: AuthenticationService = Depends(get_authentication_service),
) -> HttpToken:
    """
    Возвращает обновленный Access токен.
    """
    return await auth_service.refresh(current_user)


@auth_router.patch(
    '/patch',
    response_model=HttpToken,
    summary='Обновление данных пользователя',
    description='Обновление данных пользователя.',
    dependencies=[Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.default, seconds=G_RATE_LIMIT_SETTINGS.window))],
)
@filter_exception_decorator(
    filter_error_handler=fast_api_http_error_handler,
    err_prefix_msg='Failed to change personal data',
    err_logger=logger,
)
async def patch(
    form_data: Annotated[PatchFormData, Form()],
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    encoded_token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: AuthenticationService = Depends(get_authentication_service),
) -> JSONResponse:
    """
    Обновление данных пользователя.
    """
    await auth_service.update(form_data)
    http_token: HttpToken = await auth_service.prolongToken(current_user)
    return get_authorization_token_response(
        http_token=http_token,
        content={'msg': f'User=[ login={current_user.login} ]: personal data has been updated successful'},
    )


@auth_router.post(
    '/logout',
    response_model=Dict[Any, Any],
    summary='Выход из аккаунта',
    description='Отзывает Refresh токен',
    dependencies=[Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.logout, seconds=G_RATE_LIMIT_SETTINGS.window))],
)
@filter_exception_decorator(
    filter_error_handler=fast_api_http_error_handler,
    err_prefix_msg='Failed to logout the user',
    err_logger=logger,
)
async def user_logout(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    auth_service: AuthenticationService = Depends(get_authentication_service),
) -> Dict[Any, Any]:
    """
    Отзывает Refresh токен.
    """
    await auth_service.logout(current_user)
    return {'msg': 'User=[{current_user.login}]: logout successful'}


@auth_router.get(
    '/me',
    summary='Возвращает текущего пользователя',
    description='Возвращает текущего пользователя: пример авторизованного входа. При обращении к авторизованному Url AccessToken перевыпускает, Refresh токен - продлевается',
    dependencies=[Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.me, seconds=G_RATE_LIMIT_SETTINGS.window))],
)
@filter_exception_decorator(
    filter_error_handler=fast_api_http_error_handler,
    err_prefix_msg='Failed to get user summary (GET /me request)',
    err_logger=logger,
)
async def get_logged_user(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    auth_service: AuthenticationService = Depends(get_authentication_service),
) -> JSONResponse:
    """
    Возвращает текущего пользователя.
    Пример авторизованного входа. При обращении к авторизованному Url AccessToken перевыпускает, Refresh токен - продлевается.
    """
    http_token: HttpToken = await auth_service.prolongToken(current_user)
    return get_authorization_token_response(http_token, content=current_user)


@auth_router.get(
    '/history',
    summary='Возвращает историю входов пользователя',
    description='История входов',
    dependencies=[Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.history, seconds=G_RATE_LIMIT_SETTINGS.window))],
)
async def get_user_history(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    auth_service: AuthenticationService = Depends(get_authentication_service),
    loginhistory_service: LoginHistoryService = Depends(get_loginhistory_service),
    page_number: int = Query(ge=1, default=1, description='Номер страницы (минимум 1)'),
    page_size: int = Query(ge=1, le=100, default=50, description='Размер страницы (от 1 до 100)'),
) -> list[LoginHistoryItemDTO]:
    """
    Возвращает историю входов пользователя.
    Пример авторизованного входа. При обращении к авторизованному Url AccessToken перевыпускает, Refresh токен - продлевается.
    """
    try:
        await auth_service.prolongToken(current_user)
        return await loginhistory_service.list_(current_user=current_user, page_number=page_number, page_size=page_size)
    except Exception:
        raise get_auth_error(err_msg='Failed to refresh token pair', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@sso_router.get(
    '/login/yandex',
    summary='Вход через Яндекс',
    description='Возвращает URL для редиректа на страницу аутентификации Яндекс',
    response_description='URL для редиректа на Яндекс OAuth',
)
async def yandex_login(request: Request):
    try:
        redirect_response = await yandex_sso.get_login_redirect(request=request)
        return {"redirect_url": redirect_response.headers['location']}
    except Exception as e:
        logger.error(f"Ошибка при получении URL для редиректа на Яндекс: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@sso_router.get(
    '/login/vk',
    summary='Вход через ВКонтакте',
    description='Возвращает URL для аутентификации через ВКонтакте',
    response_description='URL для редиректа на VK OAuth',
)
async def vk_login(request: Request):
    try:
        redirect_response = await vk_sso.get_login_redirect(request=request)
        return {"redirect_url": redirect_response.url}
    except Exception as e:
        logger.error(f"Ошибка при получении URL для ВКонтакте: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@auth_router.get('/callback/yandex', include_in_schema=False)
async def yandex_callback(
    request: Request,
    auth_service: AuthenticationService = Depends(get_authentication_service),
    loginhistory_service: LoginHistoryService = Depends(get_loginhistory_service),
):
    try:
        sso_user = await yandex_sso.verify_and_process(request)
        logger.info(f"Получены данные пользователя: {sso_user}")

        user_data = SSOUserData(
            provider='yandex',
            sso_id=sso_user.id,
            email=sso_user.email,
            display_name=sso_user.display_name,
            additional_data={
                'first_name': sso_user.first_name,
                'last_name': sso_user.last_name,
                'display_name': sso_user.display_name,
                'email': sso_user.email,
            },
        )
        return await auth_service.handle_sso_user(
            sso_user=user_data, request=request, loginhistory_service=loginhistory_service
        )

    except Exception as e:
        logger.error(f'Неожиданная ошибка при авторизации через Яндекс: {str(e)}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Не удалось авторизоваться через Яндекс')


@auth_router.get('/callback/vk', include_in_schema=False)
async def vk_callback(
    request: Request,
    auth_service: AuthenticationService = Depends(get_authentication_service),
    loginhistory_service: LoginHistoryService = Depends(get_loginhistory_service),
):
    try:
        sso_user = await vk_sso.verify_and_process(request)
        user_data = SSOUserData(
            provider='vk',
            sso_id=sso_user.id,
            email=sso_user.email,
            display_name=sso_user.display_name,
            additional_data=sso_user.raw_data,
        )
        return await auth_service.handle_sso_user(
            sso_user=user_data, request=request, loginhistory_service=loginhistory_service
        )

    except Exception as e:
        logger.error(f'VK SSO error: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Не удалось авторизоваться через ВКонтакте'
        )


@auth_router.get(
    '/filter',
    summary='Возвращает список пользователей по фильтру',
    description='Возвращает список пользователей по фильтру',
    dependencies=[Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.me, seconds=G_RATE_LIMIT_SETTINGS.window))],
    response_model=List[UserInDB],
)
@filter_exception_decorator(
    filter_error_handler=fast_api_http_error_handler,
    err_prefix_msg='Failed to get user summary (GET /me request)',
    err_logger=logger,
)
@requires_permission('role:read')
async def filter(
    user_filter: UserFilter,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    auth_service: AuthenticationService = Depends(get_authentication_service),
) -> List[UserInDB]:
    """
    Возвращает пользователя(ей) по фильтру.
    """
    return await auth_service.get_by_filter(user_filter=user_filter)
