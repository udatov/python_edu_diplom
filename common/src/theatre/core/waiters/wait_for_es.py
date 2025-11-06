import os
import time
from dataclasses import asdict, dataclass

from elasticsearch import Elasticsearch


@dataclass
class ESConfig:
    scheme: str = os.environ.get('ELASTIC_SCHEME', 'http')
    host: str = os.environ.get('ELASTIC_HOST', 'localhost')
    port: int = int(os.environ.get('ELASTIC_PORT', '0')) or 9200


def wait_for_elastic():
    connection_params = ESConfig()
    es_client = Elasticsearch([asdict(connection_params)])

    while True:
        try:
            if es_client.ping():
                print('Connected to Elasticsearch.')
                return
        except Exception as e:
            print(e)

        time.sleep(0.5)
        print('Connection to Elasticsearch failed, retrying...')


if __name__ == '__main__':
    wait_for_elastic()
