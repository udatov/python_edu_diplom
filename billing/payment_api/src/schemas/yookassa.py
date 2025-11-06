import datetime
from enum import StrEnum, auto
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict
from yookassa.domain.response import PaymentResponse
from yookassa.domain.models.amount import Amount
from yookassa.domain.models.payment_data.response.authorization_details import AuthorizationDetails
from yookassa.domain.models.payment_data.recipient import Recipient

"""
Описание модели платежа Yookassa на основе https://yookassa.ru/developers/api#payment_object.
Сгенерировано с помощью https://jsontopydantic.com/.
"""


class YookassaPaymentStatus(StrEnum):
    """
    Статус платежа Yookassa: https://yookassa.ru/developers/payment-acceptance/getting-started/payment-process#lifecycle
    PENDING
    SUCCEEDED
    CANCELED
    WAITING_FOR_CAPTURE
    """

    pending = auto()
    succeeded = auto()
    canceled = auto()
    waiting_for_capture = auto()


class YookassaPayment(BaseModel):
    id: str
    created_at: datetime.datetime
    paid: bool
    status: str
    amount: Optional[Amount] = None
    authorization_details: Optional[AuthorizationDetails] = None
    description: Optional[str] = None
    expires_at: Optional[datetime.datetime] = None
    payment_method: Optional[Any] = None
    recipient: Optional[Recipient] = None
    refundable: bool = False
    test: bool = False
    income_amount: Amount = None

    model_config = ConfigDict(strict=False, arbitrary_types_allowed=True)

    @staticmethod
    def create(payment_response: PaymentResponse):
        payment_status: str = payment_response.status
        if payment_response.test and payment_response.paid:
            payment_status = YookassaPaymentStatus.succeeded
        return YookassaPayment(
            id=payment_response.id,
            status=payment_status,
            paid=payment_response.paid,
            amount=payment_response.amount,
            authorization_details=payment_response.authorization_details,
            created_at=payment_response.created_at,
            description=payment_response.description,
            expires_at=payment_response.expires_at,
            metadata=payment_response.metadata,
            income_amount=payment_response.income_amount,
            test=payment_response.test,
        )
