from enum import StrEnum, auto
from typing import Any, Dict
from typing_extensions import TypedDict
import logging
from logging import config as logging_config
from pydantic import TypeAdapter, ValidationError
from common.src.theatre.core.helpers import get_error_details
from common.src.theatre.core.logger import G_LOGGING_BASE

G_LOGGING = G_LOGGING_BASE
G_LOGGING['handlers']['file_json']['filename'] = './logs/app.log'

# Применяем настройки логирования
logging_config.dictConfig(G_LOGGING)

logger = logging.getLogger(__name__)


class ResponseLevel(StrEnum):
    info = auto()
    error = auto()
    exception = auto()
    payload = auto()
    warning = auto()


class ApiResponse(TypedDict):
    msg: str
    details: str
    level: ResponseLevel
    status: int
    payload: Dict[str, Any]

    @staticmethod
    def validate_dict_response(dict_resp: Dict[str, Any]) -> 'ApiResponse':
        if not dict_resp:
            return None
        try:
            ta = TypeAdapter(ApiResponse)
            return ta.validate_python(dict_resp)
        except ValidationError as e:
            logger.error(msg=get_error_details(error=e))
            return None
