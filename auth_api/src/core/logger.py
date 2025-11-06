from common.src.theatre.core.logger import G_LOGGING_BASE

G_LOGGING = G_LOGGING_BASE
G_LOGGING['handlers']['file_json']['filename'] = './logs/auth_api/app.log'
