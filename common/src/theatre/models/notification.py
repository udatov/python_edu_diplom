from enum import StrEnum, auto
import json
from logging import getLogger
from typing import Any, Dict, List

from pydantic import BaseModel
from sqlalchemy import Column, Enum

from common.src.theatre.core.events import NotificationEvent
from common.src.theatre.core.helpers import cls_to_str
from common.src.theatre.models.base_orm import IdOrmBase
from common.src.theatre.schemas.notifications import ContextModelType
from sqlalchemy.orm import Mapped

logger = getLogger(__name__)


class NotificationState(StrEnum):
    # Принято для отправки в очередь: модель уведомления прошла валидацию на уровне Notification API
    ACCEPT_STATE = auto()
    # Уведомление запланировано для отправки
    SCHEDULE_STATE = auto()
    # Отброшено для отправки в очередь: модель уведомления не прошла валидацию на уровне Notification API
    REJECT_STATE = auto()
    # Publisher поставил в очередь
    QUEUE_STATE = auto()
    # Потребитель получил уведомление
    ACK_STATE = auto()
    # Потребителю не удалось получить уведомление: уведомление поставлено повторно в очередь
    # Уведомление может быть поставлено до n-раз в очередь, далее уходит в очередь DLX
    REQUEUED_STATE = auto()
    DLX_STATE = auto()


class Notification(IdOrmBase):
    __tablename__ = 'notifications'
    # Состояние уведомления:
    # Принято (ACCEPT),
    # Отброшено в результате ошибок валидации в Notification API (REJECT)
    # Поставлено в очередь (QUEUE)
    # Принято консьюмером из очереди (ACK)
    # Поставлено повторно в очерердь (REDEQUE)
    # Отправлено в Dead Letter Exchange из-за ошибок на стороне потребителя (DLX)
    state = Column(Enum(NotificationState))
    # События, результатом которого стало данное уведомление
    event = Column(Enum(NotificationEvent))
    # Адресаты
    recepient_jsb_list = Mapped[List[str]]
    # Данные контекста
    context_data_jsb_list: Mapped[Dict[str, Any]]

    def __init__(
        self,
        state: NotificationState,
        event: NotificationEvent,
        recepient_list: List[str],
        context_data_dict: Dict[ContextModelType, BaseModel],
    ) -> None:
        self.state = state
        self.event = event
        self.recepient_jsb_list = json.dumps(recepient_list)

        transformed_context_data_dict: Dict[str, Any] = {}
        for k, v in context_data_dict.items():
            transformed_context_data_dict[cls_to_str(k)] = v
        self.context_data_jsb_list = json.dumps(transformed_context_data_dict)

    def __repr__(self) -> str:
        return f'<Notification ID=[{self.id}]>'
