from logging import getLogger
from typing import Any, List, Optional
from pydantic.type_adapter import TypeAdapter
from sqlalchemy import Result, ScalarResult, Sequence, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, aliased
from sqlalchemy.sql import select

from common.src.theatre.core.exception_handler import filter_exception_decorator, sql_alchemy_error_handler
from common.src.theatre.db.base import DBAuth, DBIdCRUD, DBType, UniversalReadDB
from auth_api.src.models.role import Role, user_role
from auth_api.src.models.user import User
from common.src.theatre.schemas.auth_schemas import LoginHistoryItemDTO, UserInDB
from common.src.theatre.schemas.model_filters import UserFilter
from common.src.theatre.schemas.role_schemas import RoleInDB, RoleCreate, RoleUpdate
from auth_api.src.models.permission import Permission, role_permission
from common.src.theatre.schemas.permission_schemas import PermissionInDB
from auth_api.src.models.loginhistoryitem import LoginHistoryItem


logger = getLogger(__name__)


class UserDB(UniversalReadDB, DBIdCRUD, DBAuth):
    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to find User ORM Base: based on id',
        err_logger=logger,
    )
    async def get_by_id(self, id: str, type: DBType = DBType.USER) -> Optional[UserInDB]:
        """Возвращает DTO объект из базы по его id.

        - type: тип запрашиваемого объекта
        - id: id запрашиваемого объекта
        """
        orm_user: User = await self._db_session.get(User, ident=id)
        return UserInDB(
            id=orm_user.id,
            login=orm_user.login,
            email=orm_user.email,
            first_name=orm_user.first_name,
            last_name=orm_user.last_name,
            roles=[RoleInDB.model_validate(role) for role in orm_user.roles],
        )

    async def get_by_sso_id(self, provider: str, sso_id: str) -> Optional[UserInDB]:
        """Возвращает DTO объект из базы по provider и sso_id.

        - provider: провайдер авторизации (yandex, vk, etc.)
        - sso_id: id пользователя в системе провайдера
        """
        query = select(User).where(and_(User.provider == provider, User.sso_id == sso_id))
        result = await self._db_session.execute(query)
        orm_user = result.scalar_one_or_none()

        if not orm_user:
            return None

        return UserInDB(
            id=orm_user.id,
            login=orm_user.login,
            email=orm_user.email,
            first_name=orm_user.first_name,
            last_name=orm_user.last_name,
            roles=[RoleInDB.model_validate(role) for role in orm_user.roles],
        )

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to find User ORM Base: based on login',
        err_logger=logger,
    )
    async def get_by_login(self, login: str, type: DBType = DBType.USER) -> Optional[UserInDB]:
        orm_user: User = await self._get_orm_base_by_login(login=login)
        if not orm_user:
            return None
        return UserInDB(
            id=orm_user.id,
            login=orm_user.login,
            email=orm_user.email,
            first_name=orm_user.first_name,
            last_name=orm_user.last_name,
            roles=[RoleInDB.model_validate(role) for role in orm_user.roles],
        )

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to find User ORM Base: based on filter',
        err_logger=logger,
    )
    async def get_by_filter(self, user_filter: UserFilter, type: DBType = DBType.USER) -> List[UserInDB]:
        orm_user_list: List[User] = await self._get_orm_base_by_filter(user_filter=user_filter)
        return [
            UserInDB(
                id=orm_user.id,
                login=orm_user.login,
                email=orm_user.email,
                first_name=orm_user.first_name,
                last_name=orm_user.last_name,
                roles=[RoleInDB.model_validate(role) for role in orm_user.roles],
            )
            for orm_user in orm_user_list
        ]

    async def _get_orm_base_by_login(self, login: str, type: DBType = DBType.USER) -> Optional[User]:
        """Возвращает DTO объект из базы по его login.

        - type: тип запрашиваемого объекта
        - id: id запрашиваемого объекта
        """
        query = select(User).where(User.login == login)
        result: Result = await self._db_session.execute(query)
        scalars: ScalarResult = result.scalars()
        rows: Sequence = scalars.fetchall()
        if len(rows) == 0:
            return None
        if len(rows) > 1:
            raise Exception(f'More than one rows found by user login={login}')
        return rows[0]

    async def _get_orm_base_by_filter(self, user_filter: UserFilter, type: DBType = DBType.USER) -> List[User]:
        """Возвращает DTO объект(ы) из базы по фильтру.

        - type: тип запрашиваемого объекта
        - filter: пользовательский фильтр
        """
        conditions = []

        if user_filter.id:
            conditions.append(User.id == user_filter.id)

        if hasattr(user_filter, 'ids') and user_filter.ids:
            conditions.append(User.id.in_(user_filter.ids))

        if user_filter.login:
            conditions.append(User.login == user_filter.login)

        if user_filter.email:
            conditions.append(User.email == user_filter.email)

        query = select(User).where(or_(*conditions))
        result: Result = await self._db_session.execute(query)
        scalars: ScalarResult = result.scalars()
        rows: Sequence = scalars.fetchall()
        return rows

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to check password of an User ORM Base',
        err_logger=logger,
    )
    async def check_password(self, login: str, password: str, type: DBType = DBType.USER) -> bool:
        orm_user: User = await self._get_orm_base_by_login(login=login)
        if not orm_user:
            return False
        return orm_user.check_password(password=password)

    async def _get_orm_base_by_id(self, id: str, type: DBType = DBType.USER) -> Optional[User]:
        """Возвращает ORM объект из базы по его id.

        - type: тип запрашиваемого объекта
        - id: id запрашиваемого объекта
        """
        return await self._db_session.get(User, ident=id)

    async def get_by_id_list(self, ids: list[str], type: DBType = DBType.USER) -> Optional[List[UserInDB]]:
        """Возвращает список объектов из базы по их id.

        - type_: тип запрашиваемого объекта
        - ids: список id запрашиваемоых объектов
        """
        pass

    async def search(
        self,
        type_: DBType,
        query: str,
        fields: list[str],
        page_number: int,
        page_size: int,
    ) -> list[dict[str, Any]]:
        """Возвращает список объектов из базы соответствующих критериям поиска.

        - type_: тип запрашиваемого объекта
        - query: строка запроса
        - fields: список полей для поиска
        - page_number: номер страницы результатов
        - page_size: верхняя граница количества элементов в ответе
        """
        pass

    async def list_(
        self, page_number: int, page_size: int, sort: Optional[str] = None, type: DBType = DBType.USER
    ) -> list[dict[str, Any]]:
        """Возвращает список объектов из базы с сортировкой по полю.

        - type_: тип запрашиваемого объекта
        - page_number: номер страницы результатов
        - page_size: верхняя граница количества элементов в ответе
        - fields: список полей для поиска
        - sort: строка сортировки, содержит поле и опционально "-" в начале
        """

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to create User ORM Base: sql alchemy error',
        err_logger=logger,
    )
    async def create(self, entity_dto: UserInDB) -> Optional[UserInDB]:
        user: User = User(**entity_dto.model_dump())
        self._db_session.add(user)
        await self._db_session.commit()
        await self._db_session.refresh(user)

        #  Все новые пользователи имеют базовую роль - viewer
        viewer_role_query = select(Role).where(Role.name == 'viewer')
        role_result = await self._db_session.execute(viewer_role_query)
        role = role_result.scalars().first()
        stmt = user_role.insert().values(user_id=user.id, role_id=role.id)

        await self._db_session.execute(stmt)
        await self._db_session.commit()
        await self._db_session.refresh(user)

        # Возвращаем на веб уровень dto-объект: это безопасно с точки зрения работы с сессиями SQL Alchemy: см. + валидация
        # https://docs.sqlalchemy.org/en/20/tutorial/orm_data_manipulation.html
        # return UserInDB.model_validate(user)
        return UserInDB(
            id=user.id,
            login=user.login,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            roles=[RoleInDB.model_validate(role, from_attributes=True) for role in user.roles],
        )

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to update User ORM Base: sql alchemy error',
        err_logger=logger,
    )
    async def update(self, entity_dto: UserInDB) -> bool:
        user: User = await self._get_orm_base_by_id(id=entity_dto.id)
        await user.update(db_session=self._db_session, entity_dto=entity_dto)

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to delete User ORM Base with specified id',
        err_logger=logger,
    )
    async def delete(self, entity_dto: User) -> bool:
        user_to_delete: User = await self._get_orm_base_by_id(id=entity_dto.id)
        if user_to_delete:
            await self._db_session.delete(user_to_delete)
            await self._db_session.flush()
        return True

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to get all roles',
        err_logger=logger,
    )
    async def get_all_roles(self) -> List[RoleInDB]:
        """Возвращает список всех ролей в системе."""
        query = select(Role).options(selectinload(Role.permissions))
        result: Result = await self._db_session.execute(query)
        roles = result.scalars().all()
        return [RoleInDB.model_validate(role, from_attributes=True) for role in roles]

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to assign role to user',
        err_logger=logger,
    )
    async def assign_role_to_user(self, user_id: str, role_id: str) -> bool:
        """Назначает роль пользователю."""
        user_query = select(User).where(User.id == user_id)
        role_query = select(Role).where(Role.id == role_id)

        user_result = await self._db_session.execute(user_query)
        role_result = await self._db_session.execute(role_query)

        user = user_result.scalars().first()
        role = role_result.scalars().first()

        if not user or not role:
            return False

        exists_query = select(user_role).where(and_(user_role.c.user_id == user_id, user_role.c.role_id == role_id))
        exists_result = await self._db_session.execute(exists_query)
        if exists_result.first():
            return True

        stmt = user_role.insert().values(user_id=user_id, role_id=role_id)
        await self._db_session.execute(stmt)
        await self._db_session.commit()

        return True

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to remove role from user',
        err_logger=logger,
    )
    async def remove_role_from_user(self, user_id: str, role_id: str) -> bool:
        """Отзывает роль у пользователя."""
        user_query = select(User).where(User.id == user_id)
        role_query = select(Role).where(Role.id == role_id)

        user_result = await self._db_session.execute(user_query)
        role_result = await self._db_session.execute(role_query)

        user = user_result.scalars().first()
        role = role_result.scalars().first()

        if not user or not role:
            return False

        stmt = user_role.delete().where(and_(user_role.c.user_id == user_id, user_role.c.role_id == role_id))
        await self._db_session.execute(stmt)
        await self._db_session.commit()

        return True

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to check if user has role',
        err_logger=logger,
    )
    async def check_user_has_role(self, user_id: str, role_name: str) -> bool:
        """Проверяет наличие роли у пользователя."""
        query = (
            select(Role).join(user_role).where(and_(user_role.c.user_id == user_id, Role.name == role_name)).limit(1)
        )

        result: Result = await self._db_session.execute(query)
        return result.scalars().first() is not None

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to check if user has permission',
        err_logger=logger,
    )
    async def check_user_has_permission(self, user_id: str, permission_name: str) -> bool:
        """Проверяет наличие права у пользователя через его роли."""
        RoleAlias = aliased(Role)

        query = (
            select(Permission)
            .join(role_permission, Permission.id == role_permission.c.permission_id)
            .join(RoleAlias, RoleAlias.id == role_permission.c.role_id)
            .join(user_role, RoleAlias.id == user_role.c.role_id)
            .where(and_(user_role.c.user_id == user_id, Permission.name == permission_name))
            .limit(1)
        )

        result: Result = await self._db_session.execute(query)
        return result.scalars().first() is not None

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to get user permissions',
        err_logger=logger,
    )
    async def get_user_permissions(self, user_id: str) -> List[PermissionInDB]:
        """Получает список всех прав пользователя."""
        # Прямой запрос для получения всех разрешений пользователя
        query = (
            select(Permission)
            .join(role_permission, Permission.id == role_permission.c.permission_id)
            .join(user_role, role_permission.c.role_id == user_role.c.role_id)
            .where(user_role.c.user_id == user_id)
            .distinct()
        )

        result: Result = await self._db_session.execute(query)
        permissions = result.scalars().all()

        return [PermissionInDB.model_validate(permission, from_attributes=True) for permission in permissions]

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to get role permissions',
        err_logger=logger,
    )
    async def get_role_permissions(self, role_id: str) -> List[PermissionInDB]:
        """Получает список всех прав роли."""
        query = (
            select(Permission)
            .join(role_permission, Permission.id == role_permission.c.permission_id)
            .where(role_permission.c.role_id == role_id)
        )

        result: Result = await self._db_session.execute(query)
        permissions = result.scalars().all()

        return [PermissionInDB.model_validate(permission, from_attributes=True) for permission in permissions]

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to assign permission to role',
        err_logger=logger,
    )
    async def assign_permission_to_role(self, role_id: str, permission_id: str) -> bool:
        """Назначает право роли."""
        role_query = select(Role).where(Role.id == role_id)
        permission_query = select(Permission).where(Permission.id == permission_id)

        role_result = await self._db_session.execute(role_query)
        permission_result = await self._db_session.execute(permission_query)

        role = role_result.scalars().first()
        permission = permission_result.scalars().first()

        if not role or not permission:
            return False

        exists_query = select(role_permission).where(
            and_(role_permission.c.role_id == role_id, role_permission.c.permission_id == permission_id)
        )
        exists_result = await self._db_session.execute(exists_query)
        if exists_result.first():
            return True

        stmt = role_permission.insert().values(role_id=role_id, permission_id=permission_id)
        await self._db_session.execute(stmt)
        await self._db_session.commit()

        return True

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to remove permission from role',
        err_logger=logger,
    )
    async def remove_permission_from_role(self, role_id: str, permission_id: str) -> bool:
        """Отзывает право у роли."""
        role_query = select(Role).where(Role.id == role_id)
        permission_query = select(Permission).where(Permission.id == permission_id)

        role_result = await self._db_session.execute(role_query)
        permission_result = await self._db_session.execute(permission_query)

        role = role_result.scalars().first()
        permission = permission_result.scalars().first()

        if not role or not permission:
            return False

        stmt = role_permission.delete().where(
            and_(role_permission.c.role_id == role_id, role_permission.c.permission_id == permission_id)
        )
        await self._db_session.execute(stmt)
        await self._db_session.commit()

        return True

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to create role',
        err_logger=logger,
    )
    async def create_role(self, role_data: RoleCreate) -> RoleInDB:
        """Создаёт новую роль в системе."""
        role = Role(name=role_data.name, description=role_data.description)
        self._db_session.add(role)
        await self._db_session.commit()
        await self._db_session.refresh(role)
        return RoleInDB.model_validate(role, from_attributes=True)

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to get role by id',
        err_logger=logger,
    )
    async def get_role_by_id(self, role_id: str) -> Optional[Role]:
        """Получает роль по её ID."""
        role = await self._db_session.get(Role, role_id)
        return role

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to update role',
        err_logger=logger,
    )
    async def update_role(self, role_id: str, role_data: RoleUpdate) -> bool:
        """Обновляет информацию о существующей роли."""
        role = await self._db_session.get(Role, role_id)
        if not role:
            return False

        if role_data.name is not None:
            role.name = role_data.name
        if role_data.description is not None:
            role.description = role_data.description

        self._db_session.add(role)
        await self._db_session.commit()
        return True

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to delete role',
        err_logger=logger,
    )
    async def delete_role(self, role_id: str) -> bool:
        """Удаляет существующую роль из системы."""
        role = await self._db_session.get(Role, role_id)
        if not role:
            return False

        await self._db_session.delete(role)
        await self._db_session.commit()
        return True


class LoginHistoryItemDB(UniversalReadDB, DBIdCRUD):
    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to find User ORM Base: based on id',
        err_logger=logger,
    )
    async def list_(
        self, page_number: int, page_size: int, user: UserInDB, type: DBType = DBType.LOGINHISTORYITEM
    ) -> Optional[list[LoginHistoryItemDTO]]:
        """Возвращает список объектов из базы с сортировкой по полю.

        - type_: тип запрашиваемого объекта
        - page_number: номер страницы результатов
        - page_size: верхняя граница количества элементов в ответе
        - fields: список полей для поиска
        - sort: строка сортировки, содержит поле и опционально "-" в начале
        """
        query = (
            select(LoginHistoryItem)
            .where(LoginHistoryItem.user_id == user.id)
            .limit(page_size)
            .offset(page_size * (page_number - 1))
        )
        result: Result = await self._db_session.execute(query)
        scalars: ScalarResult = result.scalars()
        rows: Sequence = scalars.fetchall()
        ta = TypeAdapter(List[LoginHistoryItemDTO])
        return ta.validate_python(rows)

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to create LoginHistoryItem ORM Base: sql alchemy error',
        err_logger=logger,
    )
    async def create(self, entity_dto: LoginHistoryItemDTO) -> Optional[LoginHistoryItemDTO]:
        loginhistoryitem: LoginHistoryItem = LoginHistoryItem(
            user_id=entity_dto.user_id, ip_address=entity_dto.ip_address
        )
        self._db_session.add(loginhistoryitem)
        await self._db_session.commit()
        await self._db_session.refresh(loginhistoryitem)
        # Возвращаем на веб уровень dto-объект: это безопасно с точки зрения работы с сессиями SQL Alchemy: см. + валидация
        # https://docs.sqlalchemy.org/en/20/tutorial/orm_data_manipulation.html
        return LoginHistoryItemDTO(
            user_id=loginhistoryitem.user_id,
            ip_address=loginhistoryitem.ip_address,
            login_datetime=loginhistoryitem.login_datetime,
        )

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to update User ORM Base: sql alchemy error',
        err_logger=logger,
    )
    async def update(self, entity_dto: LoginHistoryItem) -> bool:
        loginhistoryitem: LoginHistoryItem = await self._get_orm_base_by_id(id=entity_dto.id)
        await loginhistoryitem.update(db_session=self._db_session, user_dto=entity_dto)

    async def _get_orm_base_by_id(self, id: str, type: DBType = DBType.LOGINHISTORYITEM) -> Optional[User]:
        """Возвращает ORM объект из базы по его id.

        - type: тип запрашиваемого объекта
        - id: id запрашиваемого объекта
        """
        return await self._db_session.get(LoginHistoryItem, ident=id)

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to delete LoginHistoryItem ORM Base with specified id',
        err_logger=logger,
    )
    async def delete(self, entity_dto: LoginHistoryItem) -> bool:
        loginhistoryitem_to_delete: LoginHistoryItem = await self._get_orm_base_by_id(id=entity_dto.id)
        if loginhistoryitem_to_delete:
            await self._db_session.delete(loginhistoryitem_to_delete)
            await self._db_session.flush()
        return True

    async def get_by_id(self, type: DBType, id: str) -> Optional[dict[str, Any]]:
        pass

    async def search(
        self,
        type_: DBType,
        query: str,
        fields: list[str],
        page_number: int,
        page_size: int,
    ) -> list[dict[str, Any]]:
        """Возвращает список объектов из базы соответствующих критериям поиска.

        - type_: тип запрашиваемого объекта
        - query: строка запроса
        - fields: список полей для поиска
        - page_number: номер страницы результатов
        - page_size: верхняя граница количества элементов в ответе
        """
        pass

    async def get_by_id_list(self, ids: list[str], type: DBType = DBType.LOGINHISTORYITEM) -> Optional[List[UserInDB]]:
        """Возвращает список объектов из базы по их id.

        - type_: тип запрашиваемого объекта
        - ids: список id запрашиваемоых объектов
        """
        pass
