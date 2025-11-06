FROM email_worker_base AS email_worker

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/opt/app/:/opt/app/site-packages" \
    PATH="${PATH}:/opt/app/site-packages/bin" \
    APP_HOME=/opt/app \
    APP_USER=user

COPY email-worker/src ./email-worker/src
COPY email-worker/entry-point.sh ./email-worker/entry-point.sh

EXPOSE 8013

ENTRYPOINT ["/bin/bash", "-c", "/opt/app/email-worker/entry-point.sh"]
