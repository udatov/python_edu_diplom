from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from common.src.theatre.models.base import UUIDMixin
from common.src.theatre.schemas.permission_schemas import PermissionInDB


class RoleBase(BaseModel):
    """Базовый класс для схем ролей"""

    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    """DTO для создания роли"""

    pass


class RoleUpdate(RoleBase):
    """DTO для обновления роли"""

    pass


class RoleInDB(UUIDMixin, RoleBase):
    """DTO для получения роли из БД"""

    permissions: Optional[List[PermissionInDB]] = []

    model_config = ConfigDict(from_attributes=True)


class UserRole(BaseModel):
    """DTO для назначения/отзыва роли пользователю"""

    user_id: str
    role_id: str
    roles: Optional[List[RoleInDB]] = []

    model_config = ConfigDict(from_attributes=True)


class UserRoleCheck(BaseModel):
    """DTO для проверки наличия роли у пользователя"""

    user_id: str
    role_name: str


class UserPermissionCheck(BaseModel):
    """DTO для проверки наличия права у пользователя"""

    user_id: str
    permission_name: str
