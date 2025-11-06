import os
import time
from dataclasses import asdict, dataclass

from redis import Redis


@dataclass
class RedisConfig:
    host: str = os.environ.get('REDIS_HOST', 'localhost')
    port: int = int(os.environ.get('REDIS_PORT', '0')) or 6379


def wait_for_redis():
    connection_params = RedisConfig()
    r = Redis(**asdict(connection_params))

    while True:
        try:
            if r.ping():
                print('Connected to Redis.')
                return
        except Exception as err:
            print(err)
        time.sleep(0.5)

        print('Connection to Redis failed, retrying...')


if __name__ == '__main__':
    wait_for_redis()
