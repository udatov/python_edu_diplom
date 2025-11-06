import json
from typing import Any, Optional, Self, TypeVar
from uuid import uuid4
from logging import getLogger

from pydantic import UUID4, BaseModel, Field
from sqlalchemy.orm import declarative_base

logger = getLogger(__name__)

T = TypeVar('T', bound=BaseModel)
R = TypeVar('R')


class UUIDMixin(BaseModel):
    """
    Базовый миксин для добавления UUID
    """

    id: UUID4 = Field(default_factory=uuid4)


class BaseDBModel(BaseModel):
    """Базовый класс модели, инициализируемой по данным из эластика"""

    @classmethod
    def from_db(cls, doc: Optional[dict[str, Any]]) -> Optional[Self]:
        return cls(**doc) if doc else None

    @classmethod
    def list_from_db(cls, doc: list[dict[str, Any]]) -> list[Self]:
        return [cls(**obj) for obj in doc]

    @staticmethod
    def create_model_with_validation(model: type[T], raw_data: Any) -> R:
        try:
            load_data: Any = json.loads(raw_data)
            if isinstance(load_data, list):
                return [model.model_validate(load_it) for load_it in load_data]
            else:
                return model.model_validate(load_data) if load_data else None
        except (json.JSONDecodeError, TypeError) as json_decoder_err:
            logger.error('Ошибка при загрузке модели из raw_data: %s', json_decoder_err)
            raise json_decoder_err


# Создаём базовый класс для будущих моделей
# see more: https://docs.sqlalchemy.org/en/13/orm/extensions/declarative/basic_use.html
Base = declarative_base()
