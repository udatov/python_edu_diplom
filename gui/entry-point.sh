#! /bin/bash

set -o errexit

G_ETC=/opt/app

python3 "${G_ETC}/common/src/theatre/core/waiters/wait_for_auth_api.py" && \
    python3 "${G_ETC}/common/src/theatre/core/waiters/wait_for_payment_api.py"
    
python3 -m fastapi run "${G_ETC}/gui/src/main.py" --port 8008