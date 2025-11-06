from typing import Any, Dict

from nicegui import app
from common.src.theatre.core.auth import decode_token
from common.src.theatre.schemas.auth_schemas import HttpToken, UserSubject
from gui.src.core.config import G_GUI_SERVICE_SETTINGS


async def extract_user() -> UserSubject:
    if not is_authenticated():
        return None
    payload: Dict[str, Any] = await decode_token(
        access_token=app.storage.user.get(G_GUI_SERVICE_SETTINGS.session_secret_key)
    )
    if payload is None:
        del app.storage.user[G_GUI_SERVICE_SETTINGS.session_secret_key]
        return None
    return UserSubject.model_validate_json(payload.get('sub'))


def is_authenticated() -> bool:
    return app.storage.user.get(G_GUI_SERVICE_SETTINGS.session_secret_key) is not None


async def set_token(login_response: Dict[str, Any]):
    http_token = HttpToken.model_validate(login_response['json'])
    app.storage.user[G_GUI_SERVICE_SETTINGS.session_secret_key] = http_token.access_token


def reset_token():
    del app.storage.user[G_GUI_SERVICE_SETTINGS.session_secret_key]


def get_token():
    return app.storage.user[G_GUI_SERVICE_SETTINGS.session_secret_key]
