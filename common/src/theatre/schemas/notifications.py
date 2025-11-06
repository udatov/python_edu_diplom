from pydantic import BaseModel, EmailStr, Field, model_validator

from typing import List, Dict, Optional, Generic, Type, TypeVar, Union

from common.src.theatre.core.events import NotificationEvent
from common.src.theatre.models.base import UUIDMixin
from common.src.theatre.models.notification import NotificationState

ContextModelType = TypeVar('ContextModelType', bound=Type[UUIDMixin])


class NotificationView(BaseModel):
    """
    Представление уведомления.
    Содержит тип события, которое послужило созданию уведомления (:field: `поле <NotificationEvent.event>`).
    :field: `поле <NotificationEvent.context_data_ref>` явл. словарем, где ключ - модель данных (DTO-класс, например, UserInDB),
    а значение - список уникальных ключей, которые являются primary key в хранилище данной модели.
    """

    state: NotificationState = Field(default=NotificationState.ACCEPT_STATE)
    event: NotificationEvent
    context_data_ref_list: Dict[ContextModelType, List[str]] = Field(default={})


class AddressNotificationView(NotificationView):
    email_list: Optional[List[str]]
    recepient_roles: Optional[List[str]]

    @model_validator(mode='after')
    def check_email_or_login(self):
        if (not self.email_list or len(self.email_list) == 0) and (
            not self.recepient_roles or len(self.recepient_roles) == 0
        ):
            raise ValueError('Either email list or recepient roles are required')
        return self


class NotificationInDB(UUIDMixin):
    """
    Модель уведомления (DTO-класс), который описывает запись уведомления в БД
    (см `Уведомление в БД <notification.notification_api.src.models.notification.Notification>`).
    :field: `поле <NotificationInDB.context_data_dict>` явл. словарем, где ключ - модель данных (DTO-класс, например, UserInDB),
    а значение - список ключей данной модели (например, List[str]).
    """

    state: NotificationState
    event: NotificationEvent

    recepient_list: List[Union[EmailStr, str]]
    context_data_ref_list: Dict[ContextModelType, List[str]]


class NotificationContextFilter(Generic[ContextModelType]):
    event: NotificationEvent
    model_filter_dict: Dict[ContextModelType, BaseModel]
