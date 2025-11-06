import uuid

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from common.src.theatre.models.base import Base
from auth_api.src.models.permission import role_permission

user_role = Table(
    'user_role',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True),
)


class Role(Base):
    __tablename__ = 'roles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))

    users = relationship('User', secondary=user_role, back_populates='roles')
    permissions = relationship('Permission', secondary=role_permission, back_populates='roles', lazy='selectin')

    def __init__(self, name: str, description: str = None) -> None:
        self.name = name
        self.description = description

    def __repr__(self) -> str:
        return f'<Role {self.name}>'
