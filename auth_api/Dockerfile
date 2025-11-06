FROM auth_api_base AS auth_api

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/opt/app/:/opt/app/site-packages" \
    PATH="${PATH}:/opt/app/site-packages/bin" \
    APP_HOME=/opt/app \
    APP_USER=user

COPY auth_api/src ./auth_api/src
COPY auth_api/entry-point.sh ./auth_api/entry-point.sh

EXPOSE 8000

ENTRYPOINT ["/bin/bash", "-c", "/opt/app/auth_api/entry-point.sh"]