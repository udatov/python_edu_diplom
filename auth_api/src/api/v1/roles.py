from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_limiter.depends import RateLimiter

from auth_api.src.api.v1.auth import get_current_user
from auth_api.src.core.config import G_RATE_LIMIT_SETTINGS
from auth_api.src.core.dependencies import requires_permission
from common.src.theatre.schemas.auth_schemas import UserInDB
from common.src.theatre.schemas.role_schemas import RoleCreate, RoleInDB, RoleUpdate, UserRole, UserRoleCheck
from auth_api.src.services.access import AccessControlService, get_access_control_service
from auth_api.src.services.role import RoleService, get_role_service

role_router = APIRouter(
    prefix='',
    tags=['roles'],
    responses={404: {'description': 'Not Found'}},
)


@role_router.get(
    '/roles',
    response_model=List[RoleInDB],
    summary='Просмотр всех ролей',
    description='Возвращает список всех доступных ролей в системе',
    dependencies=[Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.role_read, seconds=G_RATE_LIMIT_SETTINGS.window))],
)
@requires_permission('role:read')
async def get_all_roles(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    access_control_service: AccessControlService = Depends(get_access_control_service),
    role_service: RoleService = Depends(get_role_service),
) -> List[RoleInDB]:
    """
    Возвращает список всех ролей в системе.
    Требует авторизации.
    """
    return await role_service.get_all_roles()


@role_router.post(
    '/users/roles',
    status_code=status.HTTP_200_OK,
    summary='Назначение роли пользователю',
    description='Назначает указанную роль пользователю',
    dependencies=[Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.user_role, seconds=G_RATE_LIMIT_SETTINGS.window))],
)
@requires_permission('role:write')
async def assign_role_to_user(
    user_role: UserRole,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    access_control_service: AccessControlService = Depends(get_access_control_service),
    role_service: RoleService = Depends(get_role_service),
) -> dict:
    """
    Назначает роль пользователю.
    Требует авторизации.

    - user_id: ID пользователя, которому назначается роль
    - role_id: ID роли, которая назначается
    """
    result = await role_service.assign_role_to_user(user_id=user_role.user_id, role_id=user_role.role_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Не удалось назначить роль пользователю {user_role.user_id}',
        )
    return {'status': 'success', 'message': 'Роль успешно назначена пользователю'}


@role_router.delete(
    '/users/roles',
    status_code=status.HTTP_200_OK,
    summary='Отзыв роли у пользователя',
    description='Отзывает указанную роль у пользователя',
    dependencies=[Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.user_role, seconds=G_RATE_LIMIT_SETTINGS.window))],
)
@requires_permission('role:write')
async def remove_role_from_user(
    user_role: UserRole,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    access_control_service: AccessControlService = Depends(get_access_control_service),
    role_service: RoleService = Depends(get_role_service),
) -> dict:
    """
    Отзывает роль у пользователя.
    Требует авторизации.

    - user_id: ID пользователя, у которого отзывается роль
    - role_id: ID роли, которая отзывается
    """
    result = await role_service.remove_role_from_user(user_id=user_role.user_id, role_id=user_role.role_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Не удалось отозвать роль у пользователя {user_role.user_id}',
        )
    return {'status': 'success', 'message': 'Роль успешно отозвана у пользователя'}


@role_router.post(
    '/users/roles/check',
    status_code=status.HTTP_200_OK,
    summary='Проверка наличия роли у пользователя',
    description='Проверяет, имеет ли пользователь указанную роль',
    dependencies=[Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.role_read, seconds=G_RATE_LIMIT_SETTINGS.window))],
)
@requires_permission('role:read')
async def check_user_has_role(
    check_data: UserRoleCheck,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    access_control_service: AccessControlService = Depends(get_access_control_service),
    role_service: RoleService = Depends(get_role_service),
) -> dict:
    """
    Проверяет наличие роли у пользователя.
    Требует авторизации.

    - user_id: ID пользователя, для которого проверяется наличие роли
    - role_name: Название роли, которую нужно проверить
    """
    has_role = await role_service.check_user_has_role(user_id=check_data.user_id, role_name=check_data.role_name)
    return {'has_role': has_role}


@role_router.post(
    '/roles',
    response_model=RoleInDB,
    status_code=status.HTTP_201_CREATED,
    summary='Создание новой роли',
    description='Создаёт новую роль с указанными параметрами',
    dependencies=[Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.role_write, seconds=G_RATE_LIMIT_SETTINGS.window))],
)
@requires_permission('role:write')
async def create_role(
    role_data: RoleCreate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    access_control_service: AccessControlService = Depends(get_access_control_service),
    role_service: RoleService = Depends(get_role_service),
) -> RoleInDB:
    """
    Создаёт новую роль в системе.
    Требует авторизации и права 'role:write'.

    - name: Название роли
    - description: Описание роли (опционально)
    """
    return await role_service.create_role(role_data)


@role_router.get(
    '/roles/{role_id}',
    response_model=RoleInDB,
    summary='Получение роли по ID',
    description='Возвращает информацию о роли по её идентификатору',
    dependencies=[Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.role_read, seconds=G_RATE_LIMIT_SETTINGS.window))],
)
@requires_permission('role:read')
async def get_role_by_id(
    role_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    access_control_service: AccessControlService = Depends(get_access_control_service),
    role_service: RoleService = Depends(get_role_service),
) -> RoleInDB:
    """
    Возвращает информацию о роли по её ID.
    Требует авторизации и права 'role:read'.

    - role_id: ID роли
    """
    role = await role_service.get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Роль с ID {role_id} не найдена')
    return role


@role_router.put(
    '/roles/{role_id}',
    response_model=RoleInDB,
    summary='Обновление роли',
    description='Обновляет информацию о существующей роли',
    dependencies=[Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.role_write, seconds=G_RATE_LIMIT_SETTINGS.window))],
)
@requires_permission('role:write')
async def update_role(
    role_id: str,
    role_data: RoleUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    access_control_service: AccessControlService = Depends(get_access_control_service),
    role_service: RoleService = Depends(get_role_service),
) -> RoleInDB:
    """
    Обновляет информацию о существующей роли.
    Требует авторизации и права 'role:write'.

    - role_id: ID роли
    - name: Новое название роли
    - description: Новое описание роли (опционально)
    """
    updated_role = await role_service.update_role(role_id, role_data)
    if not updated_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Роль с ID {role_id} не найдена')
    return updated_role


@role_router.delete(
    '/roles/{role_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Удаление роли',
    description='Удаляет существующую роль из системы',
    dependencies=[Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.role_write, seconds=G_RATE_LIMIT_SETTINGS.window))],
)
@requires_permission('role:write')
async def delete_role(
    role_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    access_control_service: AccessControlService = Depends(get_access_control_service),
    role_service: RoleService = Depends(get_role_service),
) -> None:
    """
    Удаляет существующую роль из системы.
    Требует авторизации и права 'role:write'.

    - role_id: ID роли
    """
    success = await role_service.delete_role(role_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Роль с ID {role_id} не найдена')
