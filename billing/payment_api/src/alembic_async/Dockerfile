FROM alembic_async_base AS payment_api_alembic_async_service
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="${PYTHONPATH}:/opt/app/:/opt/app/site-packages" \
    PATH="${PATH}:/opt/app/site-packages/bin" \
    APP_HOME=/opt/app \
    APP_USER=user

COPY billing/payment_api/src/alembic_async ./billing/payment_api/src/alembic_async
COPY billing/payment_api/src/models ./billing/payment_api/src/models
COPY billing/payment_api/src/schemas ./billing/payment_api/src/schemas
COPY auth_api/src/alembic_async/entry-point.sh /opt/app/auth_api/src/alembic_async/entry-point.sh

ENTRYPOINT ["/bin/bash", "-c", "/opt/app/billing/payment_api/src/alembic_async/entry-point.sh"]

