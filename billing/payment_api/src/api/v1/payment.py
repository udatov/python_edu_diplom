from logging import getLogger
from typing import Annotated, Any, Dict
from fastapi import APIRouter, Depends, Path, Request
from fastapi.security import OAuth2PasswordBearer

from billing.payment_api.src.core.config import G_PAYMENT_SERVICE_SETTINGS
from billing.payment_api.src.schemas.payment import (
    BasePaymentView,
    SubscribeView,
    YookassaPaymentView,
)
from billing.payment_api.src.schemas.yookassa import YookassaPayment, YookassaPaymentStatus
from common.src.theatre.core.auth import G_SECURITY_JWT
from common.src.theatre.core.config import G_API_PATH_SETTINGS
from common.src.theatre.core.exception_handler import (
    fast_api_http_error_response_handler,
    filter_exception_decorator,
)
from billing.payment_api.src.services.payment import PaymentService, get_payment_service
from common.src.theatre.schemas.auth_schemas import UserSubject
from common.src.theatre.core.helpers import build_response_body
from yookassa import Payment

logger = getLogger(__name__)

"""
Описание "ручек" для проведения оплаты подписки.
Платежи проходят по сценарию работы с виджетом платежной системы - YooKassa 
(https://yookassa.ru/developers/payment-acceptance/integration-scenarios/widget/integration#payment-page-initialize-and-render).

Общий сценарий,
    1. Пользователь переходит к оплате.
    2. Вы отправляете ЮKassa запрос на создание платежа.
    3. ЮKassa возвращает вам созданный объект платежа с токеном для инициализации виджета.
    4. Вы инициализируете виджет и отображаете форму на странице оплаты или во всплывающем окне.
    5. Пользователь выбирает способ оплаты, вводит данные.
    6. При необходимости виджет перенаправляет пользователя на страницу подтверждения платежа или отображает всплывающее окно (например, для аутентификации по 3‑D Secure).
    7. Пользователь подтверждает платеж.
    8. Если по какой-то причине платеж не прошел (например, не хватило денег) и срок действия токена для инициализации виджета еще не истек, виджет отображает пользователю сообщение об ошибке и предлагает оплатить еще раз с возможностью повторно выбрать способ оплаты.
    9. Если пользователь подтвердил платеж или если закончился срок действия токена для инициализации, виджет перенаправляет пользователя на страницу завершения оплаты на вашей стороне или выполняет действия, настроенные вами для события завершения оплаты.
    10. Вы отображаете нужную информацию, в зависимости от статуса платежа.
    
Нужно заметить, потверждение платежа идет за счет YooKassa.
Завершение платежа инициируется YooKassa, сервис перенаправляет на нашу ручку /complete
Cм сюда: https://yookassa.ru/developers/payment-acceptance/integration-scenarios/widget/basics

Перезагрузка виджета.
Есть также возможность перезагрузки виджета (если на странице проведения оплаты пользователь может изменить состав заказа), тогда потребуется
создать новый платеж, при этом старый виджет (с токеном старого платежа) инвалидируется с помомщью window.YooMoneyCheckoutWidget.destroy.
Данный сценарий у нас не применим.
"""

payment_api_router = APIRouter(
    prefix='',
    responses={404: {'description': 'Not Found'}},
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='v1/payment_api/complete')


@payment_api_router.post(
    path="/subscribe",
    response_model=Dict[str, Any],
    summary='Действия по созданию платежа для покупки подписки (на основе виджета).',
    description='Возвращает объект с токеном для создания виджета. Токен имеет ограниченный срок действия - 1 час',
)
@filter_exception_decorator(
    filter_error_handler=fast_api_http_error_response_handler,
    err_prefix_msg='Failed to create payment.',
    err_logger=logger,
)
async def subscribe(
    current_user: Annotated[Dict[Any, Any], Depends(G_SECURITY_JWT)],
    request: Request,
    payment_service: PaymentService = Depends(get_payment_service),
) -> Dict[str, Any]:
    """
    Возвращает объект с токеном для создания виджета и URL для перенаправления на наш сервис со стороны YooKassa.
    Токен имеет ограниченный срок действия - 1 час.
    Создание платежа: https://yookassa.ru/developers/payment-acceptance/integration-scenarios/widget/quick-start
    Данная ручка также сохраняет в хранилище информацию о Yookassa платеже для его извлечения и проверки статуса
    в ручке /complete/{yookassa_payment_id} - см ниже.
    При создании платежа его статус устанавливается в pending, по его завершению он должен перейти либо в cancelled,
    либо succeedded.
    """
    payment = Payment.create(
        {
            "amount": {"value": "2.00", "currency": "RUB"},
            "confirmation": {"type": "embedded"},
            "capture": True,
            "description": "LONGTERM SUBSCRIPTION",
        },
        G_PAYMENT_SERVICE_SETTINGS.generate_yookassa_idempotence_key,
    )
    user_subject: UserSubject = UserSubject.model_validate_json(json_data=current_user['sub'])
    subscribe_view: SubscribeView = SubscribeView.model_validate(obj=await request.json())
    yookassa_payment_view = YookassaPaymentView(
        payer_id=user_subject.id,
        subscribe_view=subscribe_view,
        confirmation_token=payment.confirmation.confirmation_token,
        yookassa_payment_id=payment.id,
        yookassa_status=payment.status,
        return_url=f'{G_API_PATH_SETTINGS.gui_service_path}/complete/{payment.id}',
    )
    # сохраняем созданный платеж в БД: статус pending
    await payment_service.subscribe(yookassa_payment_view=yookassa_payment_view)
    # возвращаем представление с платежом
    return build_response_body(
        msg='YooKassa Payment has been created successfully',
        payload=yookassa_payment_view.model_dump(),
    )


@payment_api_router.get(
    path="/complete/{yookassa_payment_id}",
    response_model=Dict[str, Any],
    summary='Действия по завершению платежа (платеж подтвержден со стороны системы оплаты, например, вернувшийся статус платежа YooKassa = payment.succeeded)',
    description='Выполняет сопутствующие действия по завершению платежа.',
)
@filter_exception_decorator(
    filter_error_handler=fast_api_http_error_response_handler,
    err_prefix_msg='Failed to complete payment.',
    err_logger=logger,
)
async def complete(
    encoded_token: Annotated[str, Depends(oauth2_scheme)],
    yookassa_payment_id: Annotated[str, Path(title="The UUID of Yookassa payment document")],
    payment_service: PaymentService = Depends(get_payment_service),
) -> Dict[str, Any]:
    """
    Завершает платеж в зависимости от его YooKassa статуса: YooKassa перенаправляет на данный URL, в URL мы сохраняем
    идентификатор платежа Yookassa.
    То есть данная ручка должна провести сопутствующие действия по окончанию процедуры оплаты (успешный/отмененный платеж).
    Предварительно мы должны сохранить у себя в Хранилище платежный документ на стадии создания виджета,
    так как Yookassa не возвращает никакой информации в запросе на return_url - данный путь указываем при создании виджета.
    Статусы платежа по его завершению должен быть:
    - succeeded
    - canceled

    """
    yookassa_payment: YookassaPayment = await payment_service.find_in_yookassa(yookassa_payment_id=yookassa_payment_id)
    if not yookassa_payment:
        return build_response_body(
            status=400,
            level='error',
            msg=f'Failed to retrieve information about the payment in Yookass, payment_id = {yookassa_payment_id}',
        )
    if yookassa_payment.status not in [YookassaPaymentStatus.succeeded, YookassaPaymentStatus.canceled]:
        return build_response_body(
            status=400,
            level='error',
            msg=f'Unsupported YooKassa payment status {yookassa_payment.status}, payment_id = {yookassa_payment_id}',
        )

    payment_view: BasePaymentView = await payment_service.find_by_yookassa_payment(
        yookassa_payment_id=yookassa_payment.id
    )
    if not payment_view:
        return build_response_body(
            status=400,
            level='error',
            msg=f'Failed to find the payment in Database, payment_id = {yookassa_payment_id}',
        )
    return await payment_service.complete(payment_view=payment_view, user_jwt_token=encoded_token)
