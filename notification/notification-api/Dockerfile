FROM notification_api_base AS notification_api

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/opt/app/:/opt/app/site-packages" \
    PATH="${PATH}:/opt/app/site-packages/bin" \
    APP_HOME=/opt/app \
    APP_USER=user

COPY notification-api/src ./notification-api/src
COPY notification-api/entry-point.sh ./notification_api/entry-point.sh

EXPOSE 8006

ENTRYPOINT ["/bin/bash", "-c", "/opt/app/notification_api/entry-point.sh"]