FROM alembic_async_base AS auth_api_alembic_async_service
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="${PYTHONPATH}:/opt/app/:/opt/app/site-packages" \
    PATH="${PATH}:/opt/app/site-packages/bin" \
    APP_HOME=/opt/app \
    APP_USER=user

COPY auth_api/src/alembic_async ./auth_api/src/alembic_async
COPY auth_api/src/db ./auth_api/src/db
COPY auth_api/src/models ./auth_api/src/models
COPY auth_api/src/core ./auth_api/src/core
COPY auth_api/src/alembic_async/entry-point.sh /opt/app/auth_api/src/alembic_async/entry-point.sh

ENTRYPOINT ["/bin/bash", "-c", "/opt/app/auth_api/src/alembic_async/entry-point.sh"]

