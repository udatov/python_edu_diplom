import datetime
from logging import getLogger
from functools import lru_cache
from typing import Any, Dict, Optional

import httpx
from fastapi import Depends

from billing.payment_api.src.core.config import G_PAYMENT_SERVICE_SETTINGS
from billing.payment_api.src.db.rdb import PaymentDB
from billing.payment_api.src.schemas.payment import BasePaymentView, PaymentInDB
from billing.payment_api.src.schemas.yookassa import YookassaPayment, YookassaPaymentStatus
from common.src.theatre.db.base import DBIdCRUD, get_db
from common.src.theatre.services.base import IdService, ModelType
from yookassa import Payment
from yookassa.domain.response import PaymentResponse
from common.src.theatre.core.helpers import build_response_body, get_error_details

logger = getLogger(__name__)


@lru_cache()
def get_payment_service(db: DBIdCRUD = Depends(get_db)) -> IdService[ModelType]:
    """
    :param db: Экземпляр базы данных для платежей
    :return: Экземпляр сервиса платежей
    """
    return PaymentService(payment_db=db)


class PaymentService(IdService):
    """
    Сервис для обработки платежей и назначения ролей пользователям.

    Осуществляет подтверждение платежей, получение админских токенов,
    назначение роли подписчика и обновление пользовательских токенов.
    """

    def __init__(self, payment_db: PaymentDB):
        """
        :param payment_db: БД с платежами
        """
        super().__init__(payment_db)
        self.admin_jwt_token = None

    async def _get_admin_token(self) -> str:
        """
        :return: JWT access токен администратора
        """
        data = {
            "username": G_PAYMENT_SERVICE_SETTINGS.auth_defaultuser_login,
            "password": G_PAYMENT_SERVICE_SETTINGS.auth_defaultuser_password,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                G_PAYMENT_SERVICE_SETTINGS.auth_login_endpoint,
                data=data,
                headers={'content-type': 'application/x-www-form-urlencoded'},
            )
            resp.raise_for_status()
            result = resp.json()
            return result["access_token"]

    async def _get_subscriber_role_id(self, admin_jwt_token: str) -> Optional[str]:
        """
        :param admin_jwt_token: JWT токен администратора для авторизации
        :return: ID роли "subscriber", либо None если не найдена
        """
        headers = {"Authorization": f"Bearer {admin_jwt_token}"}
        async with httpx.AsyncClient() as client:
            roles_resp = await client.get(G_PAYMENT_SERVICE_SETTINGS.auth_get_roles_endpoint, headers=headers)
            roles_resp.raise_for_status()
            roles_list = roles_resp.json()
            return next(
                (role['id'] for role in roles_list if role.get("name") == G_PAYMENT_SERVICE_SETTINGS.subscriber_role),
                None,
            )

    async def subscribe(self, yookassa_payment_view: BasePaymentView) -> None:
        """
        После создания платежа Yookassa требуется его сохранить, так как
        возвращаемый запрос от Yookassa не содержит в теле информации о созданного ранее
        платеже.
        """
        payment_db: PaymentDB = self.db
        await payment_db.create(payment_view=yookassa_payment_view)

    async def find_in_yookassa(self, yookassa_payment_id: str) -> Optional[YookassaPayment]:
        """
        Ищим платеж в системе YooKassa по идентификатору в строке возврщаемого запроса - return_url.
        Формат пути возвращаемого запроса: /complete/{yookassa_payment_id}
        """
        yookassa_payment_response: PaymentResponse = Payment.find_one(payment_id=yookassa_payment_id)
        if not yookassa_payment_response:
            return None
        return YookassaPayment.create(payment_response=yookassa_payment_response)

    async def find_by_yookassa_payment(self, yookassa_payment_id: str) -> Optional[PaymentInDB]:
        """
        Ищим во внутреннем хранилище платежей.
        """
        payment_db: PaymentDB = self.db
        return await payment_db.find_by_yookassa_payment(yookassa_payment_id=yookassa_payment_id)

    async def complete(self, payment_view: PaymentInDB, user_jwt_token: str) -> Dict[str, Any]:
        """
        Алгоритм работы:
         - Создать запись о платеже
         - Получить или обновить токен администратора
         - Получить идентификатор роли "subscriber"
         - Назначить роль "subscriber" пользователю
         - Обновить access-токен пользователя

        :param payment_view: Модель с данными успешного платежа YooKassa
        :param user_jwt_token: JWT токен пользователя
        :return: тело запроса
        """
        payment_db: PaymentDB = self.db
        if payment_view.yookassa_status == YookassaPaymentStatus.succeeded:
            payment_view.ended_at = datetime.datetime.now() + datetime.timedelta(
                days=G_PAYMENT_SERVICE_SETTINGS.subscription_days
            )
        await payment_db.update(entity_dto=payment_view)
        if payment_view.yookassa_status == YookassaPaymentStatus.canceled:
            return build_response_body(
                level='warrning', status=200, msg=f'Yookassa payment id={payment_view.yookassa_payment_id} was canceled'
            )

        if not self.admin_jwt_token:
            try:
                self.admin_jwt_token = await self._get_admin_token()
            except httpx.HTTPStatusError as err:
                return build_response_body(
                    level='error', status=403, msg='Administrator login failed', details=get_error_details(error=err)
                )

        try:
            role_id = await self._get_subscriber_role_id(self.admin_jwt_token)
            if role_id is None:
                return build_response_body(
                    level='error', status=500, msg=f'Не удалось найти роль {G_PAYMENT_SERVICE_SETTINGS.subscriber_role}'
                )
        except httpx.HTTPStatusError as err:
            return build_response_body(
                level='error',
                status=500,
                msg='Ошибка получения информации о ролях',
                details=get_error_details(error=err),
            )

        user_id = str(payment_view.payer_id)
        admin_headers = {"Authorization": f"Bearer {self.admin_jwt_token}"}
        role_payload = {"user_id": user_id, "role_id": role_id}
        try:
            async with httpx.AsyncClient() as client:
                assign_resp = await client.post(
                    G_PAYMENT_SERVICE_SETTINGS.auth_assign_role_endpoint,
                    json=role_payload,
                    headers=admin_headers,
                )
                assign_resp.raise_for_status()
        except httpx.HTTPStatusError as err:
            return build_response_body(
                level='error',
                status=500,
                msg=f'Не удалось назначить роль {G_PAYMENT_SERVICE_SETTINGS.subscriber_role} пользователю {user_id}',
                details=get_error_details(error=err),
            )

        user_headers = {"Authorization": f"Bearer {user_jwt_token}"}
        refresh_url = G_PAYMENT_SERVICE_SETTINGS.auth_token_refresh_endpoint
        try:
            async with httpx.AsyncClient() as client:
                refresh_resp = await client.get(refresh_url, headers=user_headers)
                refresh_resp.raise_for_status()
                new_token = refresh_resp.json()
        except httpx.HTTPStatusError as err:
            return build_response_body(
                level='error',
                status=500,
                msg='Обновление токена не удалось',
                details=get_error_details(error=err),
            )

        try:
            subscription_end_date = payment_view.ended_at.strftime(
                "%d.%m.%Y") if payment_view.ended_at else "не указано"

            notification_payload = {
                "recipients": {
                    "user_ids": [user_id]
                },
                "channels": ["email"],
                "content": {
                    "email": {
                        "subject": "Подписка успешно оплачена!",
                        "body": {
                            "html": f"<h2>Поздравляем! Ваша подписка успешно оплачена и активирована.</h2>"
                                    f"<p><strong>Детали платежа:</strong></p>"
                                    f"<ul>"
                                    f"<li>ID платежа: {payment_view.yookassa_payment_id}</li>"
                                    f"<li>Подписка активна до: <strong>{subscription_end_date}</strong></li>"
                                    f"</ul>"
                                    f"<p>Теперь вы можете пользоваться всеми премиум-возможностями нашего сервиса!</p>"
                                    f"<p>Спасибо за доверие!</p>"
                        }
                    }
                },
                "event": {
                    "event_type": "CUSTOM",
                    "subject": "Подписка оплачена",
                    "text": f"Пользователь {user_id} успешно оплатил подписку (платеж {payment_view.yookassa_payment_id})"
                }
            }
            api_key_headers = {
                "X-API-Key": G_PAYMENT_SERVICE_SETTINGS.notification_api_key
            }
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{G_PAYMENT_SERVICE_SETTINGS.notification_service_endpoint}",
                    json=notification_payload,
                    headers=api_key_headers,
                    timeout=10.0
                )
        except Exception as err:
            logger.error(f"Ошибка отправки email-уведомления: {err}")

        return build_response_body(
            level='transport',
            status=200,
            msg='Новый токен успешно выпущен',
            payload={'new_token': new_token},
        )

    def _from_db(self, doc: dict) -> ModelType:
        """Абстрактный метод для преобразования dict в Pydantic-модель"""
        pass
