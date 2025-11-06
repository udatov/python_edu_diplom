from logging import getLogger

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import and_

from auth_api.src.models.permission import Permission, role_permission
from auth_api.src.models.role import Role, user_role
from auth_api.src.models.user import User
from auth_api.src.core.config import G_AUTH_DEFAULTUSER_SETTINGS

logger = getLogger(__name__)

DEFAULT_ROLES = [
    {'name': 'admin', 'description': 'Администратор системы с полными правами'},
    {'name': 'subscriber', 'description': 'Подписчик с дополнительными возможностями'},
    {'name': 'viewer', 'description': 'Обычный пользователь с базовыми правами'},
]

DEFAULT_PERMISSIONS = [
    {'name': 'movie:read', 'description': 'Просмотр фильмов'},
    {'name': 'movie:write', 'description': 'Редактирование фильмов'},
    {'name': 'movie:delete', 'description': 'Удаление фильмов'},
    {'name': 'user:read', 'description': 'Просмотр пользователей'},
    {'name': 'user:write', 'description': 'Редактирование пользователей'},
    {'name': 'user:delete', 'description': 'Удаление пользователей'},
    {'name': 'role:read', 'description': 'Просмотр ролей'},
    {'name': 'role:write', 'description': 'Редактирование ролей'},
    {'name': 'role:delete', 'description': 'Удаление ролей'},
    {'name': 'permission:read', 'description': 'Просмотр прав доступа'},
    {'name': 'permission:write', 'description': 'Редактирование прав доступа'},
    {'name': 'permission:delete', 'description': 'Удаление прав доступа'},
    {'name': 'premium_content:read', 'description': 'Просмотр премиум-контента'},
]

ROLE_PERMISSIONS = {
    'admin': [
        'movie:read',
        'movie:write',
        'movie:delete',
        'user:read',
        'user:write',
        'user:delete',
        'role:read',
        'role:write',
        'role:delete',
        'permission:read',
        'permission:write',
        'permission:delete',
        'premium_content:read',
    ],
    'subscriber': ['movie:read', 'premium_content:read'],
    'viewer': ['movie:read'],
}


async def seed_permissions(session: AsyncSession):
    """
    Заполняет базу данных начальными правами доступа, если они отсутствуют.
    """
    for perm_data in DEFAULT_PERMISSIONS:
        stmt = select(Permission).where(Permission.name == perm_data['name'])
        result = await session.execute(stmt)
        existing_perm = result.scalars().first()

        if not existing_perm:
            new_perm = Permission(name=perm_data['name'], description=perm_data['description'])
            session.add(new_perm)
            logger.info(f'Created permission: {perm_data["name"]}')

    await session.commit()


async def seed_roles(session: AsyncSession):
    """
    Заполняет базу данных начальными ролями, если они отсутствуют.
    """
    for role_data in DEFAULT_ROLES:
        stmt = select(Role).where(Role.name == role_data['name'])
        result = await session.execute(stmt)
        existing_role = result.scalars().first()

        if not existing_role:
            new_role = Role(name=role_data['name'], description=role_data['description'])
            session.add(new_role)
            logger.info(f'Created role: {role_data["name"]}')

    await session.commit()


async def assign_role_permissions(session: AsyncSession):
    """Назначает права доступа ролям согласно настройкам."""

    stmt = select(Role).options(selectinload(Role.permissions))
    result = await session.execute(stmt)
    roles = {role.name: role for role in result.scalars().all()}

    perm_stmt = select(Permission)
    perm_result = await session.execute(perm_stmt)
    permissions = {perm.name: perm for perm in perm_result.scalars().all()}

    existing_links = {}
    for role_name, role in roles.items():
        existing_links[role_name] = {perm.name for perm in role.permissions}

    for role_name, perm_names in ROLE_PERMISSIONS.items():
        if role_name not in roles:
            continue

        role = roles[role_name]
        for perm_name in perm_names:
            if perm_name not in permissions:
                continue

            if perm_name not in existing_links[role_name]:
                permission = permissions[perm_name]
                await session.execute(role_permission.insert().values(role_id=role.id, permission_id=permission.id))
                logger.info(f"Added permission '{perm_name}' to role '{role_name}'")

    await session.commit()


async def seed_admin_user(session: AsyncSession):
    """
    Создает пользователя admin и назначает ему роль admin, если он еще не существует.
    """
    stmt = select(User).where(User.login == 'admin')
    result = await session.execute(stmt)
    admin_user = result.scalars().first()

    if not admin_user:
        admin_user = User(**(G_AUTH_DEFAULTUSER_SETTINGS.build_user_create_dto.model_dump()))
        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)
        logger.info(f'Created admin user with id: {admin_user.id}')

    stmt = select(Role).where(Role.name == 'admin')
    result = await session.execute(stmt)
    admin_role = result.scalars().first()

    if not admin_role:
        logger.warning('Admin role not found, skipping role assignment')
        return

    stmt = select(user_role).where(
        and_(user_role.c.user_id == str(admin_user.id), user_role.c.role_id == str(admin_role.id))
    )
    result = await session.execute(stmt)

    if not result.first():
        await session.execute(user_role.insert().values(user_id=str(admin_user.id), role_id=str(admin_role.id)))
        await session.commit()
        logger.info('Assigned admin role to admin user')


async def seed_database(session: AsyncSession):
    """
    Заполняет базу данных начальными данными.
    """
    await seed_permissions(session)
    await seed_roles(session)
    await assign_role_permissions(session)
    await seed_admin_user(session)
