import time
from dataclasses import asdict

from kafka import KafkaAdminClient
from kafka.errors import NoBrokersAvailable, NodeNotReadyError
from common.src.theatre.core.config import KafkaConfig


def wait_for_kafka():
    connection_params = KafkaConfig()

    while True:
        try:
            print(f'Bootstrap servers: {connection_params.bootstrap_servers}')
            admin_client = KafkaAdminClient(**asdict(connection_params))
            admin_client.list_topics()
            admin_client.close()
            print('Connected to Kafka.')
            return
        except (NoBrokersAvailable, NodeNotReadyError) as e:
            print(f"Kafka broker not available: {e}")
        except Exception as e:
            print(f"Error connecting to Kafka: {e}")

        time.sleep(1)
        print('Connection to Kafka failed, retrying...')


if __name__ == '__main__':
    wait_for_kafka()
