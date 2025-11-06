FROM payment_api_base AS payment_api

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/opt/app/:/opt/app/site-packages" \
    PATH="${PATH}:/opt/app/site-packages/bin" \
    APP_HOME=/opt/app \
    APP_USER=user

COPY billing/payment_api/src ./billing/payment_api/src
COPY billing/payment_api/entry-point.sh ./billing/payment_api/entry-point.sh

EXPOSE 8007

ENTRYPOINT ["/bin/bash", "-c", "/opt/app/billing/payment_api/entry-point.sh"]