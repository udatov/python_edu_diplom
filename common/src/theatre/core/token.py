import datetime
from logging import getLogger
from typing import Any, Dict, Optional
from redis.asyncio import Redis
from datetime import timezone, datetime, timedelta  # noqa: F811
import jwt
from jwt import InvalidIssuerError, InvalidTokenError
from abc import ABC, abstractmethod
from Cryptodome.Random.random import getrandbits
from common.src.theatre.core.config import G_JWT_SETTINGS
from common.src.theatre.core.helpers import logging_error, seconds_between
from common.src.theatre.schemas.auth_schemas import UserSubject

logger = getLogger(__name__)

access_token_factory: Optional['BaseTokenFactory'] = None
refresh_token_factory: Optional['BaseTokenFactory'] = None


async def get_access_token_factory(token_store: Redis) -> 'BaseTokenFactory':
    return await AccessTokenFactory().set_store(store=token_store).init()


async def get_refresh_token_factory(
    depends_on_factory: 'BaseTokenFactory', token_store: Redis = None
) -> 'BaseTokenFactory':
    if depends_on_factory:
        return RefreshTokenFactory(parent_token_factory=depends_on_factory)
    else:
        refresh_token_factory = RefreshTokenFactory()
        return await refresh_token_factory.set_store(store=token_store).init()


class StoreAccessor:
    """Доступ в хранилище (Redis): требуется для отправки Redis объектам в качестве параметра (используется во время тестирования)"""

    def __init__(self, store: Redis = None):
        self._redis = store

    def set_store(self, store: Redis):
        self._redis = store
        return self

    def get_store(self):
        return self._redis


class BaseTokenCoder(ABC):
    """Базовый класс реализации кодирования/декодирования токена"""

    @abstractmethod
    def decode(self, encode_token: str, **kwargs) -> Dict[Any, Any]:
        pass

    @abstractmethod
    def encode(self, subject_claims: Dict[Any, Any], **kwargs) -> Dict[Any, Any]:
        pass


class JwtTokenCoder(BaseTokenCoder):
    """Реализация кодирования/декодирования JWT токена"""

    def decode(self, encode_token: str, secret_key: str, algorithm: str) -> Dict[Any, Any]:
        return jwt.decode(jwt=encode_token, key=secret_key, algorithms=[algorithm])

    def encode(self, subject_claims: Dict[Any, Any], secret_key: str, algorithm: str) -> str:
        return jwt.encode({**subject_claims}, key=secret_key, algorithm=algorithm)


class BaseTokenBuilder(ABC, StoreAccessor):
    """Базовый класс строителя токена"""

    @abstractmethod
    def set_algorithm(self, algorithm: str) -> 'BaseTokenBuilder':
        pass

    @abstractmethod
    def set_secret_key_strength(self, secret_key_strength: str) -> 'BaseTokenBuilder':
        pass

    @abstractmethod
    def init(self) -> 'BaseTokenBuilder':
        pass

    @abstractmethod
    def build(self, subject: Dict[Any, Any] = None, expire_delta: timedelta = timedelta(hours=1)) -> str:
        pass

    @abstractmethod
    def encode(self, subject_claims: Dict[Any, Any]) -> str:
        pass

    @abstractmethod
    def decode(self, encode_token: str) -> Dict[Any, Any]:
        pass

    @abstractmethod
    def get_token_coder(self) -> BaseTokenCoder:
        pass


class JwtTokenBuilder(BaseTokenBuilder, StoreAccessor):
    """
    Строитель JWT Token: скрывает логику обработки параметров токена и его создание
    (алгоритм шифрования, реализацию кодирования/декодирования токена и т.д.)
    """

    SUPPORT_SECRET_KEY_ALGORITHM_DICT = {
        'HS256': {
            'strength': 1024,
        },
        'RS256': {
            'strength': 2048,
        },
    }

    @classmethod
    def _generate_secret_key(cls, n: int = 1024) -> int:
        return getrandbits(n)

    def __init__(self, token_coder: BaseTokenCoder):
        self._key_strength: int = None
        self._secret_key: str = None
        self._algorithm: str = None
        self._subject: UserSubject = None
        self._char_encoding: str = None
        self._redis: Redis = None
        self._token_coder = token_coder

    def set_algorithm(self, algorithm: str) -> 'JwtTokenBuilder':
        if algorithm not in self.SUPPORT_SECRET_KEY_ALGORITHM_DICT:
            err_msg: str = f'Unsupported encoding algorithm = {algorithm}'
            logger.error(msg=err_msg)
            raise Exception(err_msg)
        self._algorithm = algorithm
        return self

    def set_secret_key_strength(self, secret_key_strength: str) -> 'JwtTokenBuilder':
        if self._algorithm is None:
            err_msg: str = 'Algorithm is not set'
            logger.error(msg=err_msg)
            raise Exception(err_msg)
        required_key_strength: int = self.SUPPORT_SECRET_KEY_ALGORITHM_DICT[self._algorithm]['strength']
        if secret_key_strength > required_key_strength:
            err_msg: str = (
                f'Secret key strength must be not less than {required_key_strength}, passed value={secret_key_strength}'
            )
            logger.error(msg=err_msg)
            raise Exception(err_msg)

        self._key_strength = secret_key_strength
        return self

    async def init(self) -> 'JwtTokenBuilder':
        redis_key_header: str = G_JWT_SETTINGS.secret_key_header

        data = await self.get_store().get(name=redis_key_header)
        if data:
            self._secret_key = str(data.decode('utf-8'))
        else:
            self._secret_key = str(self._generate_secret_key(self._key_strength))
            await self.get_store().set(name=redis_key_header, value=self._secret_key)
        return self

    def build(self, subject: UserSubject = None, expire_delta: timedelta = timedelta(hours=1)) -> str:
        subject_claims: Dict[Any, Any] = {
            'sub': subject.model_dump_json(),
            'iat': int(datetime.now(timezone.utc).timestamp()),
            'exp': int((datetime.now(timezone.utc) + expire_delta).timestamp()),
        }

        return self.encode(subject_claims=subject_claims)

    def encode(self, subject_claims: Dict[Any, Any]) -> str:
        return self.get_token_coder().encode(subject_claims, self._secret_key, algorithm=self._algorithm)

    def decode(self, encode_token: str) -> Dict[Any, Any]:
        return self.get_token_coder().decode(encode_token, self._secret_key, algorithm=self._algorithm)

    def get_token_coder(self) -> BaseTokenCoder:
        return self._token_coder


class BaseTokenFactory(ABC, StoreAccessor):
    """
    Базовая фабрика для токенов: скрывает логику параметризации и выпуска токенов,
    проксирует запросы на шифрование и дешифрование токенов
    """

    def __init__(
        self,
        parent_token_factory: 'BaseTokenFactory' = None,
        token_builder: BaseTokenBuilder = JwtTokenBuilder(token_coder=JwtTokenCoder()),
    ):
        if parent_token_factory:
            self._token_builder = parent_token_factory.get_token_builder()
            self._redis = parent_token_factory.get_store()
        else:
            self._token_builder = token_builder

    async def init(self) -> 'BaseTokenFactory':
        await (
            self.get_token_builder()
            .set_algorithm(algorithm=G_JWT_SETTINGS.alogrithm)
            .set_secret_key_strength(secret_key_strength=G_JWT_SETTINGS.secret_key_strength)
            .set_store(self.get_store())
            .init()
        )
        return self

    def get_token_builder(self):
        return self._token_builder

    def create(
        self, subject: Dict[Any, Any], expire_delta=timedelta(hours=G_JWT_SETTINGS.access_token_lifetime_hours)
    ) -> str:
        return self._token_builder.build(subject=subject, expire_delta=expire_delta)


class AccessTokenFactory(BaseTokenFactory):
    """Фабрика Access токенов: срок жизни задается через переменные среды (1 час по умолчанию), не персистентны"""


class RefreshTokenFactory(BaseTokenFactory):
    """Фабрика Refresh токенов: срок жизни задается через переменные среды (10 дней по умолчанию), токены хранятся в Redis"""

    async def create(
        self, subject: UserSubject, expire_delta=timedelta(days=G_JWT_SETTINGS.refresh_token_lifetime_days)
    ) -> str:
        subject_key: str = str(subject.id)
        data = await self.get_store().get(name=subject_key)
        if not data:
            jwt_token_str: str = self._token_builder.build(subject, expire_delta)
            days_in_sec: int = expire_delta * 24 * 60 * 60
            await self.get_store().setex(name=subject_key, time=days_in_sec, value=jwt_token_str)
            return jwt_token_str
        else:
            warn_msg: str = f'WARN: subject={subject} already has Refresh token'
            logger.warning(msg=warn_msg)


class BaseHandler(ABC):
    """Базовый класс для обработки задачи в виде цепочки действий"""

    def __init__(
        self, token_factory: BaseTokenFactory, access_token: str = None, subject: Dict[Any, Any] = None, next=None
    ):
        self._token_factory = token_factory
        self._access_token = access_token
        self._subject = subject
        self._next = next

    @abstractmethod
    async def handle(self) -> bool:
        pass

    def __repr__(self) -> str:
        return self.__class__.__name__

    def get_err_descr_header(self) -> str:
        return f'[ {self.__repr__()} ] handler failed, please, see details below. '

    def set_next(self, next: 'BaseHandler') -> 'BaseHandler':
        self._next = next
        return self

    def get_next(self) -> 'BaseHandler':
        return self._next

    async def process(self):
        h: BaseHandler = self
        while h:
            try:
                await h.handle()
                h = h.get_next()
            except Exception as token_error:
                logging_error(error=token_error, prefix_msg=self.get_err_descr_header(), logger=logger)
                raise token_error


class RefreshTokenValidityHandler(BaseHandler):
    """Обработчик валидации Refresh токенов (декодирование): токен декодируется и есть в Redis"""

    def __init__(
        self, token_factory: BaseTokenFactory, subject: UserSubject, access_token=None, next: 'BaseHandler' = None
    ):
        BaseHandler.__init__(self, token_factory=token_factory, subject=subject.model_dump(), next=next)

    async def handle(self) -> None:
        data = await self._token_factory.get_store().get(name=str(self._subject['id']))
        err_msg = f'token is absent for passed subject={self._subject};'
        is_token_absent = not data
        if is_token_absent:
            raise InvalidIssuerError(err_msg)
        return not is_token_absent


class RefreshTokenExpirationValidityHandler(BaseHandler):
    """Обработчик валидации (декодирование, даты) Refresh токенов"""

    def __init__(self, token_factory: BaseTokenFactory, subject: UserSubject, next: 'BaseHandler' = None):
        BaseHandler.__init__(self, token_factory=token_factory, subject=subject.model_dump(), next=next)

    async def handle(self) -> None:
        token_builder: BaseTokenBuilder = self._token_factory.get_token_builder()
        is_refresh_token_expired = False
        data = await self._token_factory.get_store().get(name=str(self._subject['id']))
        err_msg = ''
        if data:
            refresh_token_subject_claims: Dict[Any, Any] = token_builder.decode(encode_token=data.decode('utf-8'))
            is_refresh_token_expired = refresh_token_subject_claims['exp'] > int(datetime.now(timezone.utc).timestamp())
        else:
            err_msg = f'token is absent for passed subject={self._subject};'
        if not is_refresh_token_expired:
            err_msg = f'Token Pair is expired: access_token={self._access_token}; subject={self._subject};'
        if len(err_msg) > 0:
            raise InvalidTokenError(err_msg)


class AccessTokenExpirationValidityHandler(BaseHandler):
    """Обработчик валидации Access токена по дате"""

    def __init__(self, token_factory: BaseTokenFactory, access_token: str, next: 'BaseHandler' = None):
        BaseHandler.__init__(self, token_factory=token_factory, access_token=access_token, next=next)

    async def handle(self) -> None:
        token_builder: BaseTokenBuilder = self._token_factory.get_token_builder()
        access_token_subject_claims: Dict[Any, Any] = token_builder.decode(encode_token=self._access_token)
        is_token_expired = access_token_subject_claims['exp'] < int(datetime.now(timezone.utc).timestamp())
        if is_token_expired:
            raise InvalidTokenError(
                f'Access token is out of date: access_token={self._access_token}; subject={self._subject}'
            )


class RevokeRefreshTokenHandler(BaseHandler):
    """Обработчик отзыва Refresh токена"""

    def __init__(self, token_factory: BaseTokenFactory, subject: UserSubject, next: 'BaseHandler' = None):
        BaseHandler.__init__(
            self, token_factory=token_factory, access_token=None, subject=subject.model_dump(), next=next
        )

    async def handle(self) -> None:
        await self._token_factory.get_store().delete(str(self._subject['id']))


class ProlongRefreshTokenHandler(BaseHandler):
    """Обработчик продления Refresh токена"""

    def __init__(self, token_factory: BaseTokenFactory, subject: UserSubject, next: 'BaseHandler' = None):
        BaseHandler.__init__(
            self, token_factory=token_factory, access_token=None, subject=subject.model_dump(), next=next
        )

    async def handle(self) -> None:
        subject_key: str = str(self._subject['id'])
        data = await self._token_factory.get_store().get(name=subject_key)
        if data:
            token_builder: BaseTokenBuilder = self._token_factory.get_token_builder()
            subject_claims: Dict[Any, Any] = token_builder.decode(encode_token=data.decode('utf-8'))

            new_exp_date: datetime = datetime.fromtimestamp(subject_claims['exp']) + timedelta(
                days=G_JWT_SETTINGS.refresh_token_lifetime_days
            )
            iat_date: datetime = datetime.fromtimestamp(subject_claims['iat'])
            seconds_to_expire: int = seconds_between(d1=iat_date, d2=new_exp_date)
            if seconds_to_expire < 0:
                raise InvalidIssuerError(
                    f"Can't prolong refresh token because days_in_sec < 0 [days_in_sec={seconds_to_expire}]: subject={self._subject}"
                )
            await self._token_factory.get_store().setex(
                name=subject_key,
                time=seconds_to_expire,
                value=token_builder.encode(subject_claims),
            )
        else:
            raise InvalidTokenError(
                f"Can't prolong refresh token because user has no Refresh token: subject={self._subject}"
            )
