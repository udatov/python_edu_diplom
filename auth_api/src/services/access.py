from logging import getLogger
from typing import List, Union

from fastapi import Depends

from common.src.theatre.db.base import DBAuth, DBIdCRUD, UniversalReadDB, get_db
from common.src.theatre.schemas.permission_schemas import PermissionInDB
from auth_api.src.services.role import RoleService, get_role_service

logger = getLogger(__name__)


class AccessControlService:
    """Сервис управления доступом (RBAC)"""

    def __init__(self, db: Union[UniversalReadDB, DBIdCRUD, DBAuth], role_service: RoleService):
        """Инициализация AccessControlService"""
        self._db = db
        self._role_service = role_service

    async def check_user_has_permission(self, user_id: str, permission_name: str) -> bool:
        """
        Проверяет наличие права у пользователя через его роли.

        - user_id: Идентификатор пользователя
        - permission_name: Название права
        """
        return await self._db.check_user_has_permission(user_id=user_id, permission_name=permission_name)

    async def get_user_permissions(self, user_id: str) -> List[PermissionInDB]:
        """
        Получает список всех прав пользователя.

        - user_id: Идентификатор пользователя
        """
        return await self._db.get_user_permissions(user_id=user_id)

    async def get_role_permissions(self, role_id: str) -> List[PermissionInDB]:
        """
        Получает список всех прав роли.

        - role_id: Идентификатор роли
        """
        return await self._db.get_role_permissions(role_id=role_id)

    async def assign_permission_to_role(self, role_id: str, permission_id: str) -> bool:
        """
        Назначает право роли.

        - role_id: Идентификатор роли
        - permission_id: Идентификатор права
        """
        return await self._db.assign_permission_to_role(role_id=role_id, permission_id=permission_id)

    async def remove_permission_from_role(self, role_id: str, permission_id: str) -> bool:
        """
        Отзывает право у роли.

        - role_id: Идентификатор роли
        - permission_id: Идентификатор права
        """
        return await self._db.remove_permission_from_role(role_id=role_id, permission_id=permission_id)

    async def check_permission_for_resource(self, user_id: str, resource_type: str, action: str) -> bool:
        """
        Проверяет, имеет ли пользователь право на выполнение действия с ресурсом.

        - user_id: Идентификатор пользователя
        - resource_type: Тип ресурса (например, 'movie', 'user')
        - action: Действие (например, 'read', 'write', 'delete')
        """
        permission_name = f'{resource_type}:{action}'
        return await self.check_user_has_permission(user_id=user_id, permission_name=permission_name)


def get_access_control_service(
    db: UniversalReadDB = Depends(get_db), role_service: RoleService = Depends(get_role_service)
) -> AccessControlService:
    """Получение экземпляра AccessControlService"""
    return AccessControlService(db=db, role_service=role_service)
