from fastapi import FastAPI
from gui.src.core.logger import G_LOGGING
from gui.src.frontend import frontend
import logging
from logging import config as logging_config

unrestricted_page_routes = {'/login'}

# Применяем настройки логирования
logging_config.dictConfig(G_LOGGING)

logger = logging.getLogger(__name__)


app = FastAPI()
frontend.init(app)
