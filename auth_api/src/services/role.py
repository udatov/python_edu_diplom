from logging import getLogger
from typing import List, Union, Optional

from fastapi import Depends

from common.src.theatre.db.base import DBAuth, DBIdCRUD, UniversalReadDB, get_db
from common.src.theatre.core.redis import cache_with_storage
from common.src.theatre.schemas.role_schemas import RoleInDB, RoleCreate, RoleUpdate
from common.src.theatre.services.base import IdService

logger = getLogger(__name__)


class RoleService(IdService[RoleInDB]):
    """Сервис для работы с ролями"""

    def __init__(self, db: Union[UniversalReadDB, DBIdCRUD, DBAuth]):
        """Инициализация RoleService"""
        super().__init__(db)
        self._db = db

    def _from_db(self, doc: dict) -> RoleInDB:
        """Преобразует документ из БД в модель Pydantic"""
        if doc is None:
            return None
        return RoleInDB.model_validate(doc)

    @cache_with_storage(RoleInDB)
    async def get_all_roles(self) -> List[RoleInDB]:
        """
        Получает список всех ролей с кешированием в Redis.
        """
        roles = await self._db.get_all_roles()
        return roles

    async def assign_role_to_user(self, user_id: str, role_id: str) -> bool:
        """
        Назначает роль пользователю.

        - user_id: Идентификатор пользователя
        - role_id: Идентификатор роли
        """
        return await self._db.assign_role_to_user(user_id=user_id, role_id=role_id)

    async def remove_role_from_user(self, user_id: str, role_id: str) -> bool:
        """
        Отзывает роль у пользователя.

        - user_id: Идентификатор пользователя
        - role_id: Идентификатор роли
        """
        return await self._db.remove_role_from_user(user_id=user_id, role_id=role_id)

    async def check_user_has_role(self, user_id: str, role_name: str) -> bool:
        """
        Проверяет наличие роли у пользователя.

        - user_id: Идентификатор пользователя
        - role_name: Название роли
        """
        return await self._db.check_user_has_role(user_id=user_id, role_name=role_name)

    async def create_role(self, role_data: RoleCreate) -> RoleInDB:
        """
        Создаёт новую роль в системе.

        - role_data: Данные для создания роли
        """
        # В реальной реализации здесь должна быть логика создания роли
        return await self._db.create_role(role_data)

    async def get_role_by_id(self, role_id: str) -> Optional[RoleInDB]:
        """
        Возвращает информацию о роли по её ID.

        - role_id: ID роли
        """
        # В реальной реализации здесь должна быть логика получения роли по ID
        role = await self._db.get_role_by_id(role_id)
        return self._from_db(role) if role else None

    async def update_role(self, role_id: str, role_data: RoleUpdate) -> Optional[RoleInDB]:
        """
        Обновляет информацию о существующей роли.

        - role_id: ID роли
        - role_data: Новые данные роли
        """
        # В реальной реализации здесь должна быть логика обновления роли
        updated = await self._db.update_role(role_id, role_data)
        if updated:
            return await self.get_role_by_id(role_id)
        return None

    async def delete_role(self, role_id: str) -> bool:
        """
        Удаляет существующую роль из системы.

        - role_id: ID роли
        """
        # В реальной реализации здесь должна быть логика удаления роли
        return await self._db.delete_role(role_id)


def get_role_service(db: UniversalReadDB = Depends(get_db)) -> RoleService:
    """Получение экземпляра RoleService"""
    return RoleService(db=db)
