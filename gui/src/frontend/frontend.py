from typing import Any, Dict, Optional
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from nicegui import ui

from billing.payment_api.src.schemas.payment import SubscribeView, YookassaPaymentView
from common.src.theatre.schemas.auth_schemas import UserSubject
from gui.src.core.service import (
    make_auth_api_post_login,
    make_payment_api_post_subscribe,
    make_payment_api_get_complete,
)
from gui.src.core.config import G_YOOKASSA_WIDGET_SETTINGS, G_TAILWIND_STYLE_SETTINGS, G_GUI_SERVICE_SETTINGS

from gui.src.core.storage import extract_user, is_authenticated, reset_token, set_token

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from nicegui import app as nicegui_app

from common.src.theatre.schemas.http_api import ApiResponse

unrestricted_page_routes = {'/login'}


G_SUBSCRIBE_PARAMS_HOLDER = SubscribeView()


class AuthMiddleware(BaseHTTPMiddleware):
    """This middleware restricts access to all NiceGUI pages.

    It redirects the user to the login page if they are not authenticated.
    """

    async def dispatch(self, request: Request, call_next):
        if not is_authenticated():
            if not request.url.path.startswith('/_nicegui') and request.url.path not in unrestricted_page_routes:
                return RedirectResponse(f'/login?redirect_to={request.url.path}')
        return await call_next(request)


def check_api_response(api_dict_response: Dict[str, Any]) -> ApiResponse:

    validated_dict: ApiResponse = ApiResponse.validate_dict_response(dict_resp=api_dict_response['json'])
    is_error = (
        api_dict_response['status'] > 200
        or not api_dict_response['json']
        or not validated_dict
        or validated_dict['status'] > 200
    )

    if api_dict_response['status'] == 200 and api_dict_response['json'] and is_error:
        return api_dict_response['json']

    if is_error:
        with ui.row().classes('flex items-center w-full'):
            if api_dict_response['status'] > 200:
                ui.label(text=f'Invalid Api response. Status: {api_dict_response['status']}').classes(
                    G_TAILWIND_STYLE_SETTINGS.def_label_classes + '  text-red-500 dark:text-red-300 tracking-wide'
                )
            else:
                if validated_dict['status'] > 200:
                    ui.label(text=validated_dict['msg']).classes(
                        G_TAILWIND_STYLE_SETTINGS.def_label_classes + '  text-red-500 dark:text-red-300 tracking-wide'
                    )
                else:
                    if not validated_dict:
                        ui.label(text='Unknown Api response type').classes(
                            G_TAILWIND_STYLE_SETTINGS.def_label_classes
                            + '  text-red-500 dark:text-red-300 tracking-wide'
                        )
            return None
    return validated_dict


def init(fastapi_app: FastAPI) -> None:

    @ui.page('/home')
    async def home():
        def logout() -> None:
            reset_token()
            ui.navigate.to('/login')

        create_page_layout()
        with ui.card().classes(G_TAILWIND_STYLE_SETTINGS.card_classes):
            try:
                user_subject: UserSubject = await extract_user()
            except Exception:
                user_subject = None

            if not user_subject:
                ui.navigate.to('/login')
            else:
                with ui.column().classes('flex w-full items-center'):
                    ui.label('MANY, MANY MONTHS').classes('text-xl font-bold text-green-900 w-full text-right')
                    ui.slider(min=1, max=12, value=6).bind_value(G_SUBSCRIBE_PARAMS_HOLDER, 'lifetime_months')
                    ui.number().bind_value(G_SUBSCRIBE_PARAMS_HOLDER, 'lifetime_months').classes(
                        '!bg-gradient-to-r !from-orange-700 !to-green-800 !bg-clip-text !text-xl !font-extrabold !text-transparent w-full text-right !text-transparent'
                    )
                ui.button(
                    'Subscribe',
                    on_click=lambda: ui.navigate.to(f'/subscribe/{G_SUBSCRIBE_PARAMS_HOLDER.lifetime_months}'),
                ).classes(G_TAILWIND_STYLE_SETTINGS.btn_classes)
                ui.button('logout', on_click=logout).classes(G_TAILWIND_STYLE_SETTINGS.btn_classes)

    @ui.page('/login')
    def login(redirect_to: str = '/home') -> Optional[RedirectResponse]:
        create_page_layout()

        if is_authenticated():
            ui.navigate.to('/home')

        async def try_login() -> None:  # local function to avoid passing username and password as arguments
            login_response: Dict[str, Any] = await make_auth_api_post_login(
                username=username.value, password=password.value
            )
            api_response: ApiResponse = check_api_response(api_dict_response=login_response)
            if api_response:
                await set_token(login_response=login_response)
                ui.navigate.to(redirect_to)

        with ui.card().classes(G_TAILWIND_STYLE_SETTINGS.card_classes):
            username = (
                ui.input('Username').on('keydown.enter', try_login).classes(G_TAILWIND_STYLE_SETTINGS.input_classes)
            )
            password = (
                ui.input('Password', password=True, password_toggle_button=True)
                .on('keydown.enter', try_login)
                .classes(G_TAILWIND_STYLE_SETTINGS.input_classes)
            )
            ui.button('Log in', on_click=try_login).classes(G_TAILWIND_STYLE_SETTINGS.btn_classes)
        return None

    @ui.page('/subscribe/{months}')
    async def subscribe(months: int):
        create_page_layout()

        with ui.column().classes('absolute-center items-center'):
            with ui.row().classes('flex items-center w-full'):
                ui.label('SUBSCRIBE').classes(
                    G_TAILWIND_STYLE_SETTINGS.def_label_classes
                    + ' text-center bg-gradient-to-r from-orange-700 to-black-700 bg-clip-text text-xl font-extrabold text-transparent'
                )
                ui.html(G_YOOKASSA_WIDGET_SETTINGS.widget_html_element).classes('w-full')
            response: Dict[str, Any] = await make_payment_api_post_subscribe(months=months)
            api_response: ApiResponse = check_api_response(api_dict_response=response)
            if api_response:
                yookassa_payment: YookassaPaymentView = YookassaPaymentView.model_validate(obj=api_response['payload'])
                widget_token: str = yookassa_payment.confirmation_token
                ui.run_javascript(
                    code=G_YOOKASSA_WIDGET_SETTINGS.widget_run_js_element.format(
                        widget_token=widget_token, return_url=yookassa_payment.return_url
                    )
                )

    @ui.page('/complete/{yookassa_payment_id}')
    async def complete(yookassa_payment_id: str):
        create_page_layout()
        with ui.column().classes('absolute-center items-center'):
            with ui.row().classes('flex items-center w-full'):
                ui.label('COMPLETE SUBSCRIBTION').classes(
                    G_TAILWIND_STYLE_SETTINGS.def_label_classes
                    + ' text-center bg-gradient-to-r from-orange-700 to-black-700 bg-clip-text text-xl font-extrabold text-transparent'
                )
            response: Dict[str, Any] = await make_payment_api_get_complete(yookassa_payment_id=yookassa_payment_id)
            api_response: ApiResponse = check_api_response(api_dict_response=response)
            if api_response:
                with ui.row().classes('flex items-center w-full'):
                    ui.label(text='Congratulations! you have subscribed.').classes(
                        G_TAILWIND_STYLE_SETTINGS.def_label_classes
                        + ' text-center bg-gradient-to-r from-orange-700 to-black-700 bg-clip-text text-xl font-extrabold text-transparent'
                    )

    ui.add_head_html(G_YOOKASSA_WIDGET_SETTINGS.lib_include, shared=True)

    def create_page_layout() -> None:
        with ui.header(elevated=True).classes('items-center justify-between bg-fuchsia-900'):
            ui.label('THEATER').classes('text-white text-xl font-extrabold')
            with ui.row():
                if is_authenticated():
                    ui.link('Home', '/home').classes('font-bold text-white')
                else:
                    ui.link('Login', '/login').classes('font-bold text-white')
        #
        with ui.footer().classes('text-white bg-fuchsia-900 w-full flex items-center'):
            ui.label('All rights preserved').classes('text-center w-full')

    ui.run_with(
        fastapi_app,
        mount_path='/',  # NOTE this can be omitted if you want the paths passed to @ui.page to be at the root
        storage_secret=G_GUI_SERVICE_SETTINGS.session_secret_key,
    )


nicegui_app.add_middleware(AuthMiddleware)
