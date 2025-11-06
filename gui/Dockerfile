FROM gui_base AS gui

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/opt/app/:/opt/app/site-packages" \
    PATH="${PATH}:/opt/app/site-packages/bin" \
    APP_HOME=/opt/app \
    APP_USER=user

COPY billing/payment_api/src/core ./billing/payment_api/src/core
COPY billing/payment_api/src/schemas ./billing/payment_api/src/schemas
COPY gui/src ./gui/src
COPY gui/entry-point.sh ./gui/entry-point.sh

EXPOSE 8008

ENTRYPOINT ["/bin/bash", "-c", "/opt/app/gui/entry-point.sh"]