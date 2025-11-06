import os
import time
from dataclasses import dataclass

import requests


@dataclass
class ClickHouseConfig:
    host: str = os.environ.get('CLICKHOUSE_HOST', 'localhost')
    port: int = int(os.environ.get('CLICKHOUSE_PORT', '0')) or 8123
    user: str = os.environ.get('CLICKHOUSE_USER', 'default')
    password: str = os.environ.get('CLICKHOUSE_PASSWORD', '')


def wait_for_clickhouse():
    connection_params = ClickHouseConfig()
    url = f"http://{connection_params.host}:{connection_params.port}"

    auth = None
    if connection_params.user:
        auth = (connection_params.user, connection_params.password)

    while True:
        try:
            response = requests.get(url, auth=auth, params={'query': 'SELECT 1'}, timeout=5)
            if response.status_code == 200 and response.text.strip() == '1':
                print('Connected to ClickHouse.')
                return
            else:
                print(f"ClickHouse responded with status code {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to ClickHouse: {e}")

        time.sleep(1)
        print('Connection to ClickHouse failed, retrying...')


if __name__ == '__main__':
    wait_for_clickhouse()
