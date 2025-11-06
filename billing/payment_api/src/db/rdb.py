from logging import getLogger
from typing import Optional

from sqlalchemy import Result, ScalarResult, Select, Sequence, select

from billing.payment_api.src.models.payment import SubscribePayment
from billing.payment_api.src.schemas.payment import BasePaymentView, PaymentInDB
from common.src.theatre.core.exception_handler import filter_exception_decorator, sql_alchemy_error_handler
from common.src.theatre.db.base import DBIdCRUD, DBType
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

logger = getLogger(__name__)


class PaymentDB(DBIdCRUD):
    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to get Payment ORM entity by id: sqlalchemy error',
        err_logger=logger,
    )
    async def _get_by_id(self, id: str, type: DBType = DBType.PAYMENT) -> Optional[PaymentInDB]:
        """Возвращает ORM объект из базы по его id.

        - type: тип запрашиваемого объекта
        - id: id запрашиваемого объекта
        """
        orm_subscribe_payment: PaymentDB = await self._db_session.get(SubscribePayment, ident=id)
        return orm_subscribe_payment

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to get Payment ORM entity by id: sqlalchemy error',
        err_logger=logger,
    )
    async def get_by_id(self, id: str, type: DBType = DBType.PAYMENT) -> Optional[PaymentInDB]:
        """Возвращает DTO объект из базы по его id.

        - type: тип запрашиваемого объекта
        - id: id запрашиваемого объекта
        """
        orm_subscribe_payment: PaymentDB = await self._get_by_id(SubscribePayment, ident=id)
        return orm_subscribe_payment.create_dto() if orm_subscribe_payment else None

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to create SubscribePayment ORM entity: sqlalchemy error',
        err_logger=logger,
    )
    async def create(self, payment_view: BasePaymentView) -> PaymentInDB:
        # TO CHECK payment_view: BasePaymentView или payment_view: PaymentInDB
        orm_subscribe_payment: SubscribePayment = SubscribePayment(
            payer_id=payment_view.payer_id,
            yookassa_payment_id=payment_view.yookassa_payment_id,
            yookassa_payment_status=payment_view.yookassa_status,
            lifetime_months=payment_view.subscribe_view.lifetime_months,
            subscribe_type=payment_view.subscribe_view.subscribe_type,
        )
        self._db_session.add(orm_subscribe_payment)
        await self._db_session.commit()
        await self._db_session.refresh(orm_subscribe_payment)
        return orm_subscribe_payment.create_dto()

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to find ORM SubscribePayment',
        err_logger=logger,
    )
    async def _find_by_yookassa_payment(self, yookassa_payment_id: str) -> Optional[SubscribePayment]:
        payment_query: Select = select(SubscribePayment).where(
            SubscribePayment.yookassa_payment_id == yookassa_payment_id
        )
        payment_result: Result = await self._db_session.execute(statement=payment_query)
        subscribe_payment_scalars: ScalarResult = payment_result.scalars()
        subscribe_payment_seq: Sequence = subscribe_payment_scalars.fetchall()
        payment_doc_counts: int = len(subscribe_payment_seq)
        if payment_doc_counts == 0:
            return None
        if payment_doc_counts > 1:
            raise SQLAlchemyError(
                f'More than one Yookassa payment id document found {yookassa_payment_id}, count={payment_doc_counts}'
            )
        orm_subscribe_doc: SubscribePayment = subscribe_payment_seq[0]
        return orm_subscribe_doc

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to find ORM SubscribePayment',
        err_logger=logger,
    )
    async def find_by_yookassa_payment(self, yookassa_payment_id: str) -> Optional[PaymentInDB]:
        orm_subscribe_payment: SubscribePayment = await self._find_by_yookassa_payment(
            yookassa_payment_id=yookassa_payment_id
        )
        if not orm_subscribe_payment:
            return None
        return orm_subscribe_payment.create_dto()

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to update ORM SubscribePayment',
        err_logger=logger,
    )
    async def update(self, entity_dto: PaymentInDB) -> None:
        orm_subscribe_payment: SubscribePayment = await self._get_by_id(id=entity_dto.id)
        await orm_subscribe_payment.update(db_session=self._db_session, entity_dto=entity_dto)

    @filter_exception_decorator(
        filter_error_handler=sql_alchemy_error_handler,
        err_prefix_msg='Failed to delete ORM SubscribePayment',
        err_logger=logger,
    )
    async def delete(self, entity_dto: PaymentInDB) -> None:
        orm_subscribe_payment: SubscribePayment = await self._get_by_id(id=entity_dto.id)
        if orm_subscribe_payment:
            await self._db_session.delete(orm_subscribe_payment)
            await self._db_session.flush()
