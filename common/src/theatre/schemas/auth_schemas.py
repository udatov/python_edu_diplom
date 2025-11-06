import datetime
import secrets
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr

from typing import List, Optional, Dict
from enum import Enum

from pydantic import ConfigDict, Field

from common.src.theatre.models.base import UUIDMixin
from common.src.theatre.schemas.role_schemas import RoleInDB
from common.src.theatre.models.base_orm import IdOrmBase

""" 
Data Transfer Object для обмена данными между web слоем и слоем Data SQL Alchemt ORM/Core 
Задачи:
- хранение атрибутов модели без привязки к SQL Alchemy сессии
- валидация данных, получаемых с веб слоя перед их отправкой в БД

Почему предпочтительно отвязаться от сессии: см. @link https://docs.sqlalchemy.org/en/20/tutorial/orm_data_manipulation.html
"
An important thing to note is that attributes on the objects that we just worked with have been expired, meaning, 
when we next access any attributes on them, the Session will start a new transaction and re-load their state. 
This option is sometimes problematic for both performance reasons, or if one wishes to use the objects after closing the Session (which is known as the detached state), 
as they will not have any state and will have no Session with which to load that state, leading to “detached instance” errors. 
The behavior is controllable using a parameter called Session.expire_on_commit. More on this is at Closing a Session.
"
"""


class UserCreate(BaseModel):
    """DTO: валидирует данные с формы и отправляет на уровень SQL Alchemy ORM для сохранения"""

    login: str
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    provider: Optional[str] = None
    sso_id: Optional[str] = None

    # from_orm is depreacated, see @link https://docs.pydantic.dev/latest/concepts/models/#arbitrary-class-instances
    model_config = ConfigDict(from_attributes=True)


class AuthProvider(str, Enum):
    YANDEX = "yandex"
    VK = "vk"


class SSOUserData(BaseModel):
    """DTO для данных пользователя из социальных сетей"""

    provider: AuthProvider
    sso_id: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    raw_data: Dict = Field(default_factory=dict, exclude=True)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "provider": "yandex",
                "sso_id": "1234567890",
                "email": "user@yandex.ru",
                "display_name": "Иван Иванов",
                "first_name": "Иван",
                "last_name": "Иванов",
            }
        },
    )

    def to_user_create(self) -> UserCreate:
        """Преобразование в модель для создания пользователя"""
        return UserCreate(
            login=self.email or f"{self.provider}_{self.sso_id}",
            password=secrets.token_urlsafe(16),
            first_name=self.first_name or "",
            last_name=self.last_name or "",
        )


class UserInDB(UUIDMixin):
    """DTO: получение данных из БД и использование их на web уровне"""

    login: str
    email: EmailStr
    first_name: str
    last_name: str
    roles: Optional[List['RoleInDB']] = Field(default_factory=list)
    sso_ids: Dict[AuthProvider, str] = Field(default_factory=dict)

    # from_orm is depreacated, see @link https://docs.pydantic.dev/latest/concepts/models/#arbitrary-class-instances
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_safe(cls, db_obj: IdOrmBase) -> 'UserInDB':
        """Безопасное создание DTO из ORM объекта без автоматической загрузки связанных объектов"""
        return cls(id=db_obj.id, login=db_obj.login, first_name=db_obj.first_name, last_name=db_obj.last_name, roles=[])

    @classmethod
    def from_sso_data(cls, sso_data: SSOUserData) -> 'UserInDB':
        """Создание пользователя из данных социальной сети"""
        return cls(
            login=sso_data.email or f"{sso_data.provider}_{sso_data.sso_id}",
            first_name=sso_data.first_name or "",
            last_name=sso_data.last_name or "",
            sso_ids={sso_data.provider: sso_data.sso_id},
        )


class LoginHistoryItemDTO(BaseModel):
    """DTO: получение данных из БД и использование их на web уровне"""

    user_id: UUID
    login_datetime: datetime.datetime
    ip_address: str
    browser: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


""" 
Модель для представления Access и Refresh токенов
"""


class HttpToken(BaseModel):
    """Представление токена: перемещаем в заголовках HTTP запроса"""

    access_token: str
    token_type: str = 'Bearer'

    def authorization(self) -> str:
        return f'{self.token_type}: {self.access_token}'


class UserSubject(UserInDB):
    """Информация о пользователе, хранимая в полезной нагрузке токена"""


class RegisterFormData(BaseModel):
    login: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str


class PatchFormData(BaseModel):
    login: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str


class RedirectLogin(BaseModel):
    username: str
    password: str
    redirect_url: str
    # меняет http-method на GET,
    # в случае с аутентификацией (POST-запрос) мы перенаправляем клиента на landing page,
    # размещенную по redirect_url
    redirect_code: int = 303


if __name__ == '__main__':
    user_dto: UserInDB = UserInDB(
        id=uuid4(), email="user@local.localdomain", login='user', first_name='user', last_name='user'
    )
    user_subject: UserSubject = UserSubject.model_validate(user_dto)
    print(user_subject)
