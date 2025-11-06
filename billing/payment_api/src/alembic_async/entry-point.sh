#! /bin/bash

set -o errexit
set -o allexport

echo "PYTHONPATH=${PYTHONPATH}"

python3 common/src/theatre/core/waiters/wait_for_db.py

# Делаем автомиграцию БД
BILLING_PAYMENT_API__ALEMBIC_CONFIG=$(pwd)/billing/payment_api/src/alembic_async/alembic.ini
NOW_DATE="$(date +"%Y%m%d_%H%M")"

python3 -m alembic --config ${BILLING_PAYMENT_API__ALEMBIC_CONFIG} upgrade head
python3 -m alembic --config ${BILLING_PAYMENT_API__ALEMBIC_CONFIG} revision --autogenerate -m "New revision: ${NOW_DATE} rev."
python3 -m alembic --config ${BILLING_PAYMENT_API__ALEMBIC_CONFIG} upgrade head
