from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from .common import EmailContent, SMSContent, PushContent, EventType


class NotificationContent(BaseModel):
    """Объединенная модель содержимого уведомления"""
    email: EmailContent | None = None
    sms: SMSContent | None = None
    push: PushContent | None = None

    @model_validator(mode='after')
    def validate_content_channels(self) -> 'NotificationContent':
        if not any([self.email, self.sms, self.push]):
            raise ValueError("Должен быть указан хотя бы один тип контента")
        return self


# Модели событий
class BaseEvent(BaseModel):
    """Базовая модель события"""
    event_type: EventType
    event_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FixedEvent(BaseEvent):
    """Модель предопределенного события"""
    entity_id: str | None = None  # ID связанной сущности (фильм, комментарий и т.д.)

    @field_validator('event_type')
    @classmethod
    def validate_event_type(cls, v: EventType) -> EventType:
        if v == EventType.CUSTOM:
            raise ValueError("FixedEvent не может иметь тип CUSTOM")
        return v


class CustomEvent(BaseEvent):
    """Модель события в свободном формате"""
    event_type: EventType = EventType.CUSTOM
    subject: str | None = None
    text: str | None = None
