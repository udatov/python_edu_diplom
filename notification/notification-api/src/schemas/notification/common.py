from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, ValidationInfo, field_validator


class NotificationChannel(str, Enum):
    """Каналы доставки уведомлений"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class NotificationStatus(str, Enum):
    """Статусы уведомления"""
    NEW = "new"  # Новая
    SENT_TO_QUEUE = "sent_to_queue"  # Отправлено в RabbitMQ
    PROCESSING = "processing"  # В процессе обработки
    DELIVERED = "delivered"  # Доставлено получателю
    FAILED = "failed"  # Ошибка при отправке
    READ = "read"  # Прочитано получателем
    EXPIRED = "expired"  # Срок действия истек
    CANCELLED = "cancelled"  # Отменено
    SCHEDULED = "scheduled"  # Запланировано


class EventType(str, Enum):
    """Типы событий"""
    USER_REGISTRATION = "user_registration"
    NEW_MOVIE = "new_movie"
    NEW_SERIES_EPISODE = "new_series_episode"
    COMMENT_LIKED = "comment_liked"
    MOVIE_RECOMMENDATION = "movie_recommendation"
    POSTPONED_MOVIES_REMINDER = "postponed_movies_reminder"
    WEEKLY_DIGEST = "weekly_digest"
    CUSTOM = "custom"


class Recipients(BaseModel):
    """Модель получателей уведомления"""
    user_ids: list[str]

    @field_validator('user_ids')
    def validate_user_ids_not_empty(cls, v):
        if not v:
            raise ValueError('user_ids должен содержать хотя бы одно значение')
        return v


# Модели контента
class ContentData(BaseModel):
    """Данные для контента уведомления"""
    text: str | None = None
    html: str | None = None


class EmailContent(BaseModel):
    """Содержимое email-уведомления"""
    subject: str
    body: ContentData


class SMSContent(BaseModel):
    """Содержимое SMS-уведомления"""
    body: ContentData


class PushContent(BaseModel):
    """Содержимое push-уведомления"""
    title: str
    body: ContentData
    image_url: HttpUrl | None = None
    action_url: HttpUrl | None = None
    ttl: int | None = None  # Время жизни уведомления в секундах
