from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_limiter.depends import RateLimiter

from auth_api.src.api.v1.auth import get_current_user
from auth_api.src.core.config import G_RATE_LIMIT_SETTINGS
from common.src.theatre.schemas.auth_schemas import UserInDB
from common.src.theatre.schemas.permission_schemas import PermissionInDB, RolePermission
from common.src.theatre.schemas.role_schemas import UserPermissionCheck
from auth_api.src.services.access import AccessControlService, get_access_control_service

permission_router = APIRouter(
    prefix='',
    tags=['access_control'],
    responses={404: {'description': 'Not Found'}},
)


@permission_router.post(
    '/permissions/check',
    status_code=status.HTTP_200_OK,
    summary='Проверка наличия права у пользователя',
    description='Проверяет, имеет ли пользователь указанное право',
    dependencies=[
        Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.permission_read, seconds=G_RATE_LIMIT_SETTINGS.window))
    ],
)
async def check_user_has_permission(
    check_data: UserPermissionCheck,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    access_control_service: AccessControlService = Depends(get_access_control_service),
) -> dict:
    """
    Проверяет наличие права у пользователя.
    Требует авторизации.

    - user_id: ID пользователя, для которого проверяется наличие права
    - permission_name: Название права, которое нужно проверить
    """
    has_permission = await access_control_service.check_user_has_permission(
        user_id=check_data.user_id, permission_name=check_data.permission_name
    )
    return {'has_permission': has_permission}


@permission_router.get(
    '/users/{user_id}/permissions',
    response_model=List[PermissionInDB],
    summary='Получение прав пользователя',
    description='Возвращает список всех прав пользователя',
    dependencies=[
        Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.permission_read, seconds=G_RATE_LIMIT_SETTINGS.window))
    ],
)
async def get_user_permissions(
    user_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    access_control_service: AccessControlService = Depends(get_access_control_service),
) -> List[PermissionInDB]:
    """
    Возвращает список всех прав пользователя.
    Требует авторизации.

    - user_id: ID пользователя, для которого запрашиваются права
    """
    return await access_control_service.get_user_permissions(user_id=user_id)


@permission_router.get(
    '/roles/{role_id}/permissions',
    response_model=List[PermissionInDB],
    summary='Получение прав роли',
    description='Возвращает список всех прав роли',
    dependencies=[
        Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.permission_read, seconds=G_RATE_LIMIT_SETTINGS.window))
    ],
)
async def get_role_permissions(
    role_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    access_control_service: AccessControlService = Depends(get_access_control_service),
) -> List[PermissionInDB]:
    """
    Возвращает список всех прав роли.
    Требует авторизации.

    - role_id: ID роли, для которой запрашиваются права
    """
    return await access_control_service.get_role_permissions(role_id=role_id)


@permission_router.post(
    '/roles/permissions',
    status_code=status.HTTP_200_OK,
    summary='Назначение права роли',
    description='Назначает указанное право роли',
)
async def assign_permission_to_role(
    role_permission: RolePermission,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    access_control_service: AccessControlService = Depends(get_access_control_service),
) -> dict:
    """
    Назначает право роли.
    Требует авторизации.

    - role_id: ID роли, которой назначается право
    - permission_id: ID права, которое назначается
    """
    result = await access_control_service.assign_permission_to_role(
        role_id=role_permission.role_id, permission_id=role_permission.permission_id
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f'Не удалось назначить право роли {role_permission.role_id}'
        )
    return {'status': 'success', 'message': 'Право успешно назначено роли'}


@permission_router.delete(
    '/roles/permissions',
    status_code=status.HTTP_200_OK,
    summary='Отзыв права у роли',
    description='Отзывает указанное право у роли',
    dependencies=[
        Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.permission_write, seconds=G_RATE_LIMIT_SETTINGS.window))
    ],
)
async def remove_permission_from_role(
    role_permission: RolePermission,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    access_control_service: AccessControlService = Depends(get_access_control_service),
) -> dict:
    """
    Отзывает право у роли.
    Требует авторизации.

    - role_id: ID роли, у которой отзывается право
    - permission_id: ID права, которое отзывается
    """
    result = await access_control_service.remove_permission_from_role(
        role_id=role_permission.role_id, permission_id=role_permission.permission_id
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Не удалось отозвать право у роли {role_permission.role_id}',
        )
    return {'status': 'success', 'message': 'Право успешно отозвано у роли'}


@permission_router.post(
    '/check/resource',
    status_code=status.HTTP_200_OK,
    summary='Проверка доступа к ресурсу',
    description='Проверяет, имеет ли пользователь доступ к ресурсу для выполнения действия',
    dependencies=[
        Depends(RateLimiter(times=G_RATE_LIMIT_SETTINGS.permission_read, seconds=G_RATE_LIMIT_SETTINGS.window))
    ],
)
async def check_resource_access(
    user_id: str,
    resource_type: str,
    action: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    access_control_service: AccessControlService = Depends(get_access_control_service),
) -> dict:
    """
    Проверяет доступ пользователя к ресурсу для выполнения действия.
    Требует авторизации.

    - user_id: ID пользователя
    - resource_type: Тип ресурса ('movie', 'user', и т.д.)
    - action: Действие ('read', 'write', 'delete', и т.д.)
    """
    has_access = await access_control_service.check_permission_for_resource(
        user_id=user_id, resource_type=resource_type, action=action
    )
    return {'has_access': has_access}
