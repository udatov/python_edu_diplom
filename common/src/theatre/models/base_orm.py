import datetime
import uuid
from logging import getLogger

from sqlalchemy import Column, DateTime, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import AbstractConcreteBase

from common.src.theatre.core.exception_handler import filter_exception_decorator, sql_alchemy_error_handler
from common.src.theatre.models.base import Base, UUIDMixin

logger = getLogger(__name__)


class IdOrmBase(AbstractConcreteBase, Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.UTC))
    modified_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.UTC))

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to create User ORM Base: sql alchemy error',
        err_logger=logger,
    )
    async def update(self, db_session: AsyncSession, entity_dto: UUIDMixin) -> 'IdOrmBase':
        # Update model class variable from requested fields
        for var, value in vars(entity_dto).items():
            setattr(self, var, value) if value else None

        self.modified_at = datetime.datetime.now(datetime.UTC)
        db_session.add(self)
        await db_session.commit()
        await db_session.refresh(self)
        return self
