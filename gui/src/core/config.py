from pydantic import Field, computed_field
from pydantic_settings import BaseSettings
from billing.payment_api.src.core.config import G_PAYMENT_SERVICE_SETTINGS


class GuiServiceSettings(BaseSettings):
    auth_api_v1_prefix: str = Field(default='api/v1/auth')
    payment_api_v1_prefix: str = G_PAYMENT_SERVICE_SETTINGS.api_v1_prefix
    auth_api_path: str = Field(..., alias='AUTH_SERVICE_PATH')
    payment_api_path: str = Field(..., alias='PAYMENT_SERVICE_PATH')
    gui_path: str = Field(..., alias='GUI_SERVICE_PATH')
    session_secret_key: str = Field(..., alias='SESSION_SECRET_KEY')

    @computed_field
    @property
    def auth_api_v1_root_path(self) -> str:
        return f'{self.auth_api_path}/{self.auth_api_v1_prefix}'

    @computed_field
    @property
    def auth_api_v1_login(self) -> str:
        return f'{self.auth_api_path}/{self.auth_api_v1_prefix}/login'

    @computed_field
    @property
    def auth_api_v1_login_with_redirect(self) -> str:
        return f'{self.auth_api_path}/{self.auth_api_v1_prefix}/login_with_redirect'

    @computed_field
    @property
    def auth_api_v1_logout_path(self) -> str:
        return f'{self.auth_api_path}/{self.auth_api_v1_prefix}/logout'

    @computed_field
    @property
    def payment_api_v1_subscribe(self) -> str:
        return f'{self.payment_api_path}{self.payment_api_v1_prefix}/subscribe'

    @computed_field
    @property
    def payment_api_v1_complete(self) -> str:
        return f'{self.payment_api_path}{self.payment_api_v1_prefix}/complete'


G_GUI_SERVICE_SETTINGS = GuiServiceSettings()


class YookassaWidgetSettings(BaseSettings):

    lib_include: str = '<script src="https://yookassa.ru/checkout-widget/v1/checkout-widget.js"></script>'
    widget_html_element: str = '''
    <section id="payment-section">
        <!--Контейнер, в котором будет отображаться платежная форма-->
        <div id="payment-form"></div>
    </section>
    '''
    widget_js_element: str = '''
        <script>
        //Инициализация виджета. Все параметры обязательные.
        const checkout = new window.YooMoneyCheckoutWidget({{
            confirmation_token: "{widget_token}", //Токен, который перед проведением оплаты нужно получить от ЮKassa
            return_url: "{return_url}", //Ссылка на страницу завершения оплаты, это может быть любая ваша страница
            error_callback: function(error) {{
                console.log(error)
            }}
        }});
        //Отображение платежной формы в контейнере
        checkout.render('payment-form');
        </script>     
    '''
    widget_run_js_element: str = '''
        const checkout = new window.YooMoneyCheckoutWidget({{
            confirmation_token: "{widget_token}", //Токен, который перед проведением оплаты нужно получить от ЮKassa
            return_url: "{return_url}", //Ссылка на страницу завершения оплаты, это может быть любая ваша страница
            error_callback: function(error) {{
                console.log(error)
            }}
        }});
        checkout.render('payment-form');
    '''


G_YOOKASSA_WIDGET_SETTINGS = YookassaWidgetSettings()


class TailwindStyleSettings(BaseSettings):

    card_classes: str = (
        'absolute-center w-full max-w-sm p-4 bg-white border border-gray-200 rounded-lg shadow-sm sm:p-6 md:p-8 dark:bg-gray-800 dark:border-gray-700'
    )
    btn_classes: str = (
        'w-full text-white !bg-gray-800 hover:bg-gray-900 focus:ring-4 focus:outline-none focus:ring-gray-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center dark:bg-blue-600 dark:hover:bg-gray-800 dark:focus:ring-gray-900'
    )
    input_classes: str = (
        'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-600 dark:border-gray-500 dark:placeholder-gray-400 dark:text-white'
    )
    def_label_classes: str = 'text-sm font-medium w-full'


G_TAILWIND_STYLE_SETTINGS = TailwindStyleSettings()
