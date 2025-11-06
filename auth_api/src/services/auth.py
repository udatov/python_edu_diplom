import datetime
from functools import lru_cache
import secrets
from typing import List, Optional, Union
from fastapi import Depends, status, Request
from opentelemetry import trace

from pydantic import UUID4
from common.src.theatre.db.base import DBAuth, UniversalReadDB, DBIdCRUD, get_db, get_login_history_item_db
from common.src.theatre.core.redis import cache_with_storage
from common.src.theatre.schemas.model_filters import UserFilter
from common.src.theatre.services.base import IdService, ModelType
from auth_api.src.models.user import User
from auth_api.src.models.loginhistoryitem import LoginHistoryItem
from common.src.theatre.schemas.auth_schemas import (
    HttpToken,
    PatchFormData,
    SSOUserData,
    UserCreate,
    UserInDB,
    UserSubject,
    LoginHistoryItemDTO,
)
from common.src.theatre.core.token import (
    BaseTokenFactory,
    ProlongRefreshTokenHandler,
    RefreshTokenExpirationValidityHandler,
    RefreshTokenValidityHandler,
    RevokeRefreshTokenHandler,
)
from logging import getLogger
from common.src.theatre.core.helpers import logging_error, get_error_details
import common.src.theatre.core.token as token
from common.src.theatre.core.exception_handler import get_auth_error

logger = getLogger(__name__)
tracer = trace.get_tracer(__name__)


@lru_cache()
def get_authentication_service(db: UniversalReadDB = Depends(get_db)) -> IdService[ModelType]:
    """Получение экземпляра AuthenticationService"""
    return AuthenticationService(user_db=db)


@lru_cache()
def get_loginhistory_service(db: UniversalReadDB = Depends(get_login_history_item_db)) -> IdService[ModelType]:
    """Получение экземпляра LoginHistoryService"""
    return LoginHistoryService(loginhistoryitems_db=db)


class AuthenticationService(IdService[UserInDB]):
    def __init__(self, user_db: Union[UniversalReadDB, DBIdCRUD, DBAuth]):
        """Инициализация AuthenticationService"""
        super().__init__(user_db)
        self._user_db = user_db

    def _from_db(self, doc: dict) -> UserInDB:
        pass

    async def register(self, new_user_dto: UserCreate) -> Optional[UserInDB]:
        with tracer.start_as_current_span('register'):
            user_in_db: UserInDB = await self._user_db.get_by_login(login=new_user_dto.login)
            if user_in_db:
                raise get_auth_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    err_msg=f'Could not create new user: {new_user_dto} because the user already has registered',
                    headers={},
                )
            user_in_db = await self._user_db.create(entity_dto=new_user_dto)
            return user_in_db

    async def get_current_user(self, encoded_token: str) -> Optional[UserInDB]:
        token_factory: BaseTokenFactory = token.access_token_factory
        payload = token_factory.get_token_builder().decode(encoded_token)

        user_subject: UserSubject = UserSubject.model_validate_json(payload.get('sub'))
        if user_subject is None:
            raise get_auth_error()

        # проверяем RefreshToken в Redis, что он есть в хранилище
        await RefreshTokenValidityHandler(
            token_factory=token.refresh_token_factory,
            subject=user_subject,
        ).process()

        user_dto: UserInDB = await self.get_by_id(user_id=user_subject.id)
        if user_dto is None:
            raise get_auth_error()
        return user_dto

    async def authorize(
        self, login: str, password: str, request: Request, loginhistory_service: 'LoginHistoryService'
    ) -> HttpToken:
        # check password with User DB Model
        if not await self._user_db.check_password(login=login, password=password):
            raise get_auth_error(
                status_code=status.HTTP_403_FORBIDDEN, err_msg=f'Invalid password or login name passed: login={login}'
            )
        user_dto: UserInDB = await self._user_db.get_by_login(login=login)
        if not user_dto:
            raise get_auth_error(
                err_msg=f'Authorization request failed: no user={login} found', status_code=status.HTTP_400_BAD_REQUEST
            )
        user_subject: UserSubject = UserSubject.model_validate(user_dto)
        user_subject.id = user_dto.id
        try:
            await token.refresh_token_factory.create(subject=user_subject)
            await loginhistory_service.create(
                loginhistoryitems_dto=LoginHistoryItemDTO(
                    user_id=user_dto.id, login_datetime=datetime.datetime.now(), ip_address=request.client.host
                )
            )
        except Exception as err:
            raise get_auth_error(
                err_msg=f'Refresh token creation failed for subject = {user_subject}, err={err}',
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        # return access token, type = Bearer
        return HttpToken(access_token=token.access_token_factory.create(subject=user_subject))

    async def refresh(self, current_user_dto: UserInDB) -> HttpToken:
        """
        Обновление пары токенов:
        - отзываем старый Refresh token с проверкой наличия токена в Redis: при его отсутствии вызывается исключение
        - обновляем RefreshToke (записываем в Redis), AccessToken
        - Возвращаем закодированный AccessToken внутри HttpToken
        """
        try:
            user_subject: UserSubject = UserSubject.model_validate(current_user_dto)
            revoke_token_handler: RevokeRefreshTokenHandler = RevokeRefreshTokenHandler(
                token_factory=token.refresh_token_factory, subject=user_subject
            )
            #
            # Проверяем наличие Refresh токена в Redis и делаем его отзыв, если он есть
            #
            await RefreshTokenValidityHandler(
                token_factory=token.refresh_token_factory,
                subject=user_subject,
                next=revoke_token_handler,
            ).process()
            #
            # Выпускаем RefreshToken: создаем и сохраняем в Redis
            #
            await token.refresh_token_factory.create(subject=user_subject)
            #
            # Возвращаем на web layer закодированный AccessToken
            #
            return HttpToken(access_token=token.access_token_factory.create(subject=user_subject))

        except Exception as err:
            err_msg = f'[ AuthenticationService ]: Failed to refresh token for subject={current_user_dto}, details: {get_error_details(error=err)}'
            raise get_auth_error(
                err_msg=err_msg,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    async def prolongToken(self, current_user_dto: UserInDB) -> HttpToken:
        """
        Продлеваем Refresh токен, Access токен - перевыпскам:
        - отзываем старый Refresh token с проверкой наличия токена в Redis: при его отсутствии вызывается исключение
        - обновляем RefreshToke (записываем в Redis), AccessToken
        - Возвращаем закодированный AccessToken внутри HttpToken
        """
        try:
            user_subject: UserSubject = UserSubject.model_validate(current_user_dto)
            # выпускаем новый Access Token
            encode_token: str = token.access_token_factory.create(user_subject)
            # продлеваем Refresh Token
            prolong_token_handler: ProlongRefreshTokenHandler = ProlongRefreshTokenHandler(
                token_factory=token.refresh_token_factory, subject=user_subject
            )
            await RefreshTokenExpirationValidityHandler(
                token_factory=token.refresh_token_factory,
                subject=user_subject,
                next=prolong_token_handler,
            ).process()
            return HttpToken(access_token=encode_token)
        except Exception as err:
            err_msg = '[ AuthenticationService ]: Failed to refresh token'
            logging_error(logger=logger, error=err, prefix_msg=err_msg)
            raise err

    async def update(self, patch_form_dto: PatchFormData) -> None:
        user_in_db: UserInDB = await self._user_db.get_by_login(login=patch_form_dto.login)
        if not user_in_db:
            raise get_auth_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                err_msg=f'Could not update the user: {patch_form_dto} because the user is absent in the database',
                headers={},
            )
        id: UUID4 = user_in_db.id
        # Обновляем данные
        user_in_db = UserInDB.model_validate(patch_form_dto)
        user_in_db.id = id
        await self._user_db.update(entity_dto=user_in_db)

    async def logout(self, current_user_dto: UserInDB) -> None:
        try:
            user_subject: UserSubject = UserSubject.model_validate(current_user_dto)
            revoke_token_handler: RevokeRefreshTokenHandler = RevokeRefreshTokenHandler(
                token_factory=token.refresh_token_factory, subject=user_subject
            )
            #
            # Проверяем наличие Refresh токена в Redis и делаем его отзыв, если он есть
            #
            await RefreshTokenValidityHandler(
                token_factory=token.refresh_token_factory,
                subject=user_subject,
                next=revoke_token_handler,
            ).process()

        except Exception as err:
            raise get_auth_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                err_msg=get_error_details(error=err, prefix_msg='[ AuthenticationService ]: Failed to refresh token '),
            )

    @cache_with_storage(UserInDB)
    async def get_by_id(self, user_id: str) -> Optional[UserInDB]:
        """
        Получает пользователя по его идентификатору с кешированием в Redis.

        - user_id: Идентификатор пользователя.
        """
        return await self._user_db.get_by_id(id=user_id)

    @cache_with_storage(LoginHistoryItem)
    async def list_(self, token: str, page_size: int = 10, page_number: int = 1) -> List[User]:
        """
        Получает список вхождений пользователя с пагинацией и сортировкой.

        - token: jwt токен пользователя.
        - page_size: Количество вхождений пользователя на странице.
        - page_number: Номер страницы.
        """
        return []

    async def handle_sso_user(
        self, sso_user: SSOUserData, request: Request, loginhistory_service: 'LoginHistoryService'
    ) -> HttpToken:
        user = await self._user_db.get_by_sso_id(provider=sso_user.provider, sso_id=sso_user.sso_id)

        if not user:
            password = secrets.token_urlsafe(32)
            user = await self._user_db.create(
                UserCreate(
                    login=f"{sso_user.provider}_{sso_user.sso_id}",
                    email=sso_user.email,
                    password=password,
                    first_name=sso_user.display_name.split()[0] if sso_user.display_name else "",
                    last_name=" ".join(sso_user.display_name.split()[1:]) if sso_user.display_name else "",
                    provider=sso_user.provider,
                    sso_id=sso_user.sso_id,
                )
            )
            return await self.authorize(
                login=user.login, password=password, request=request, loginhistory_service=loginhistory_service
            )
        else:
            temp_password = secrets.token_urlsafe(32)
            return await self.authorize(
                login=user.login, password=temp_password, request=request, loginhistory_service=loginhistory_service
            )

    async def get_by_filter(self, user_filter: UserFilter) -> List[Optional[UserInDB]]:
        user_dto_list: List[UserInDB] = await self._user_db.get_by_filter(filter=user_filter)
        return user_dto_list


class LoginHistoryService(IdService[LoginHistoryItemDTO]):
    def __init__(self, loginhistoryitems_db: Union[UniversalReadDB, DBIdCRUD]):
        """Инициализация AuthenticationService"""
        super().__init__(loginhistoryitems_db)
        self.loginhistoryitems_db = loginhistoryitems_db

    def _from_db(self, doc: dict) -> LoginHistoryItemDTO:
        pass

    async def create(self, loginhistoryitems_dto: LoginHistoryItemDTO) -> Optional[LoginHistoryItemDTO]:
        return await self.loginhistoryitems_db.create(entity_dto=loginhistoryitems_dto)

    @cache_with_storage(LoginHistoryItemDTO)
    async def list_(self, current_user: UserInDB, page_size: int, page_number: int) -> List[LoginHistoryItemDTO]:
        """
        Получает список вхождений пользователя с пагинацией и сортировкой.

        - token: jwt токен пользователя.
        - page_size: Количество вхождений пользователя на странице.
        - page_number: Номер страницы.
        """
        return await self.loginhistoryitems_db.list_(page_number=page_number, page_size=page_size, user=current_user)
