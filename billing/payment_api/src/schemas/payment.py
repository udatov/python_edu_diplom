import datetime
from enum import StrEnum, auto
from typing import Any, Optional

from pydantic import UUID4, BaseModel
from typing import Tuple
from pydantic import Field

from billing.payment_api.src.schemas.yookassa import YookassaPayment, YookassaPaymentStatus
from common.src.theatre.models.base import UUIDMixin


class SubscribeType(StrEnum):
    """
    Тип подписки
    LONG_TERM - базовый на заданный период
    AUTO_RENEWAL - на заданный период с автопродлением
    """

    LONG_TERM = auto()
    AUTO_RENEWAL = auto()

    @classmethod
    def tuple(cls) -> Tuple:
        return tuple(map(lambda s: s.value, cls))


class SubscribeView(BaseModel):
    """
    DTO описывает представление подписки: то, что мы получаем в качестве запроса на начало проведения платежа
    """

    subscribe_type: SubscribeType = Field(default=SubscribeType.LONG_TERM)
    lifetime_months: int = Field(default=1)


class BasePaymentView(BaseModel):
    payer_id: UUID4
    subscribe_view: SubscribeView
    yookassa_payment_id: str
    yookassa_status: YookassaPaymentStatus
    yookassa_payment_method: Optional[Any] = None

    @classmethod
    def create(
        cls,
        payer_id: UUID4,
        yookassa_payment: YookassaPayment,
        subscribe_type: SubscribeType = SubscribeType.LONG_TERM,
        lifetime_days: int = 30,
    ):
        return BasePaymentView(
            payer_id=payer_id,
            subscribe_view=SubscribeView(subscribe_type=subscribe_type, lifetime_months=lifetime_days),
            yookassa_payment_id=yookassa_payment.id,
            yookassa_payment_method_id=yookassa_payment.payment_method,
        )


class YookassaPaymentView(BasePaymentView):
    """
    DTO описывает Yookassa платеж
    """

    confirmation_token: str
    return_url: str


class PaymentInDB(BasePaymentView, UUIDMixin):
    """
    DTO сохраненного в БД платежа
    """

    created_at: datetime.datetime
    ended_at: Optional[datetime.datetime] = None
