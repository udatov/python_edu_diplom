import json
from datetime import datetime
from uuid import UUID, uuid4
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_serializer, model_serializer

from common.src.theatre.core.request import EventRequestState


class UserEventRequest(BaseModel):
    """
    Модель для представления пользовательских событий.
    """

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    event_request_state: EventRequestState = Field(exclude=True)

    @field_serializer('id')
    def serialize_uuid(self, uuid_value: Optional[UUID]) -> Optional[str]:
        """Сериализует UUID в строку для ClickHouse."""
        return str(uuid_value) if uuid_value else None

    @field_serializer('timestamp')
    def serialize_datetime(self, dt_value: datetime) -> str:
        """Сериализует datetime в строку для ClickHouse."""
        return dt_value.isoformat()

    @model_serializer
    def ser_model(self) -> dict[str, Any]:
        return {
            'id': str(self.id),
            'timestamp': self.timestamp,
            'url': self.event_request_state.url,
            'request_method': self.event_request_state.method,
            'user_id': self.event_request_state.user_subject.id,
            'event_list': [event.value for event in self.event_request_state.event_list],
        }

    @classmethod
    async def from_kafka_message(
        cls, message_value: bytes, message_key: Optional[bytes] = None, timestamp: Optional[int] = None
    ) -> "UserEventRequest":
        """
        Создает экземпляр UserEventRequest из сообщения Kafka.
        """
        try:
            payload = json.loads(message_value.decode('utf-8'))
            event_request_state: EventRequestState = EventRequestState(
                http_request_state=payload,
                user_subject=await EventRequestState.async_user_subject(http_request_state=payload),
            )
            return UserEventRequest(event_request_state=event_request_state, timestamp=timestamp)

        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Ошибка создания UserEvent из сообщения Kafka: {e}")

    def to_clickhouse_dict(self) -> Dict[str, Any]:
        """
        Преобразует экземпляр UserEvent в словарь для вставки в ClickHouse.
        """
        return self.ser_model()
