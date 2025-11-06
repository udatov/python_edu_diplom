from logging import getLogger

from sqlalchemy import Column, String, Index
from sqlalchemy.orm import relationship
from werkzeug.security import check_password_hash, generate_password_hash

from common.src.theatre.models.base_orm import IdOrmBase

logger = getLogger(__name__)


class User(IdOrmBase):
    __tablename__ = 'users'

    login = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    provider = Column(String, nullable=True)
    sso_id = Column(String, nullable=True)

    roles = relationship('Role', secondary='user_role', back_populates='users', lazy="selectin")
    yandex_id = Column(String, unique=True, nullable=True)
    vk_id = Column(String, unique=True, nullable=True)

    __table_args__ = (Index('idx_provider_sso_id', 'provider', 'sso_id'),)

    def __init__(
        self,
        login: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        provider: str = None,
        sso_id: str = None,
    ) -> None:
        self.login = login
        self.email = email
        self.password = generate_password_hash(password)
        self.first_name = first_name
        self.last_name = last_name
        self.provider = provider
        self.sso_id = sso_id

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password, password)

    def __repr__(self) -> str:
        return f'<User {self.login}>'
