from typing import Optional

from pydantic import BaseModel, ConfigDict

from common.src.theatre.models.base import UUIDMixin


class PermissionBase(BaseModel):
    """Базовый класс для схем прав доступа"""

    name: str
    description: Optional[str] = None


class PermissionCreate(PermissionBase):
    """DTO для создания права доступа"""

    pass


class PermissionUpdate(PermissionBase):
    """DTO для обновления права доступа"""

    pass


class PermissionInDB(UUIDMixin, PermissionBase):
    """DTO для получения права доступа из БД"""

    model_config = ConfigDict(from_attributes=True)


class RolePermission(BaseModel):
    """DTO для назначения/отзыва права доступа роли"""

    role_id: str
    permission_id: str
