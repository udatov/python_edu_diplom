import logging
import uuid
from functools import cached_property
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings
from yookassa import Configuration

logger = logging.getLogger(__name__)


class PaymentServiceSettings(BaseSettings):
    api_v1_prefix: str = Field(default='/api/v1/payment')
    path: str = Field(..., alias='PAYMENT_SERVICE_PATH')
    subscriber_role: str = Field(default='subscriber', alias='SUBSCRIBER_ROLE')
    subscription_days: int = Field(default=30, alias='SUBSCRIPTION_DAYS')
    auth_host: str = Field(default='http://localhost:8000', alias='AUTH_SERVICE_HOST')
    auth_api_base: str = Field(default='/api/v1/auth', alias='AUTH_API_BASE')
    auth_defaultuser_login: str = Field(default='admin', alias='AUTH_DEFAULTUSER_LOGIN')
    auth_defaultuser_password: str = Field(default='admin', alias='AUTH_DEFAULTUSER_PASSWORD')
    yookassa_shopid: int = Field(..., alias='PAYMENT_YOOKASSA_SHOP_ID')
    yookassa_session_secret_key: str = Field(..., alias='PAYMENT_YOOKASSA_SECRET_API')

    notification_api_key: str = Field(...)
    notification_host: str = Field('http://notification_service:8006', alias='NOTIFICATION_HOST')
    notification_api_base: str = Field('/api/v1/notifications', alias='NOTIFICATION_API_BASE')

    def model_post_init(self, __context):
        Configuration.configure(
            account_id=self.yookassa_shopid, secret_key=self.yookassa_session_secret_key, logger=logger
        )
        return super().model_post_init(__context)

    @computed_field
    @cached_property
    def api_v1_base_path(self) -> str:
        return f'{self.path}{self.api_v1_prefix}'

    @computed_field
    @cached_property
    def auth_api_v1_url(self) -> str:
        return f"{self.auth_host}{self.auth_api_base}"

    @computed_field
    @cached_property
    def notification_api_v1_url(self) -> str:
        return f"{self.notification_host}{self.notification_api_base}"

    @computed_field
    @cached_property
    def auth_assign_role_endpoint(self) -> str:
        return f"{self.auth_api_v1_url}/users/roles"

    @computed_field
    @cached_property
    def auth_get_roles_endpoint(self) -> str:
        return f"{self.auth_api_v1_url}/roles"

    @computed_field
    @cached_property
    def auth_token_refresh_endpoint(self) -> str:
        return f"{self.auth_api_v1_url}/refresh"

    @computed_field
    @cached_property
    def auth_login_endpoint(self) -> str:
        return f"{self.auth_api_v1_url}/login"

    @property
    def generate_yookassa_idempotence_key(self) -> str:
        return str(uuid.uuid4())

    @computed_field
    @cached_property
    def notification_service_endpoint(self) -> str:
        return f"{self.notification_api_v1_url}/send"


G_PAYMENT_SERVICE_SETTINGS = PaymentServiceSettings()
