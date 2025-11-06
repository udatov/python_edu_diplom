#! /bin/bash

set -o errexit

G_ETC=/opt/app

python3 "${G_ETC}/common/src/theatre/core/waiters/wait_for_redis.py" \
    && python3 "${G_ETC}/common/src/theatre/core/waiters/wait_for_db.py" \
    && python3 "${G_ETC}/common/src/theatre/core/waiters/wait_for_auth_api.py"
    
python3 -m fastapi run "${G_ETC}/billing/payment_api/src/main.py" --port 8007