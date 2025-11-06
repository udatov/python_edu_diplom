#! /bin/bash

set -o errexit
set -o allexport

echo "PYTHONPATH=${PYTHONPATH}"

python3 common/src/theatre/core/waiters/wait_for_db.py

# Делаем автомиграцию БД
AUTH_API__ALEMBIC_CONFIG=$(pwd)/auth_api/src/alembic_async/alembic.ini
NOW_DATE="$(date +"%Y%m%d_%H%M")"

# Подхватит кастомную миграцию versions/1d159ba9eb4c_partition_loginhistoryitems_20250323_1045_rev.py
python3 -m alembic --config ${AUTH_API__ALEMBIC_CONFIG} upgrade head
python3 -m alembic --config ${AUTH_API__ALEMBIC_CONFIG} revision --autogenerate -m "New revision: ${NOW_DATE} rev."
python3 -m alembic --config ${AUTH_API__ALEMBIC_CONFIG} upgrade head
