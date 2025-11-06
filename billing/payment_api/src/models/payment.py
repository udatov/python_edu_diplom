from logging import getLogger
import uuid
from sqlalchemy import Column, DateTime, Integer, String, UUID
from billing.payment_api.src.schemas.payment import PaymentInDB, SubscribeView, SubscribeType
from common.src.theatre.models.base_orm import IdOrmBase
from sqlalchemy.types import Enum

logger = getLogger(__name__)


class SubscribePayment(IdOrmBase):
    """
    Модель платежей для оформления подписки.
    Хранит только подтвержденные (Yookassa succedded) платежи.
    """

    __tablename__ = 'subscribe_payment'

    """
    UUID Пользователя из auth сервиса
    """
    payer_id = Column(UUID(as_uuid=True), primary_key=False, default=uuid.uuid4, unique=False, nullable=False)

    """
    Тип подписки
    """
    subscribe_type = Column(Enum(SubscribeType), nullable=False)

    """
    Время действия платежа в месяцах
    """
    lifetime_months = Column(Integer, nullable=False)

    """
    Дата окончания действия подписки
    """
    ended_at = Column(DateTime(timezone=True), nullable=True)

    """
    Идентификатор платежа в YooKassa
    """
    yookassa_payment_id = Column(String, nullable=True)

    """
    Статус платежа в YooKassa
    """
    yookassa_payment_status = Column(String, nullable=True)

    def __init__(
        self,
        payer_id: uuid.UUID,
        yookassa_payment_id: str,
        yookassa_payment_status: str,
        lifetime_months: int,
        subscribe_type: SubscribeType = SubscribeType.LONG_TERM,
    ) -> None:
        self.payer_id = payer_id
        self.yookassa_payment_id = yookassa_payment_id
        self.yookassa_payment_status = yookassa_payment_status
        self.lifetime_months = lifetime_months
        self.subscribe_type = subscribe_type

    def __repr__(self) -> str:
        return f'<Payment ID=[{self.id}]>'

    def create_dto(self) -> PaymentInDB:
        return PaymentInDB(
            id=self.id,
            payer_id=self.payer_id,
            created_at=self.created_at,
            ended_at=self.ended_at,
            subscribe_view=SubscribeView(
                subscribe_type=self.subscribe_type,
                lifetime_months=self.lifetime_months,
            ),
            yookassa_payment_id=self.yookassa_payment_id,
            yookassa_status=self.yookassa_payment_status,
        )
