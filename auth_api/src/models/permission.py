import uuid

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from common.src.theatre.models.base import Base

role_permission = Table(
    'role_permission',
    Base.metadata,
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id'), primary_key=True),
)


class Permission(Base):
    __tablename__ = 'permissions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255))

    roles = relationship('Role', secondary=role_permission, back_populates='permissions', lazy='selectin')

    def __init__(self, name: str, description: str = None) -> None:
        self.name = name
        self.description = description

    def __repr__(self) -> str:
        return f'<Permission {self.name}>'
