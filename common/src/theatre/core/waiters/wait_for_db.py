import os
import time
from dataclasses import asdict, dataclass
from typing import TypeAlias

from psycopg2 import connect
from psycopg2.extensions import connection, cursor

Psycopg2Conn: TypeAlias = connection
Psycopg2Cursor: TypeAlias = cursor


@dataclass
class PGConfig:
    dbname: str = os.environ.get('POSTGRES_DB', 'postgres')
    user: str = os.environ.get('POSTGRES_USER', 'postgres')
    password: str = os.environ.get('POSTGRES_PASSWORD', 'secret')
    host: str = os.environ.get('POSTGRES_HOST', 'localhost')
    port: int = int(os.environ.get('POSTGRES_PORT', '0')) or 5432


def wait_for_db():
    connection_params = PGConfig()
    while True:
        try:
            conn: Psycopg2Conn = connect(**asdict(connection_params))
            with conn.cursor() as cursor:
                cursor.execute('Select 1;')
                _ = cursor.fetchone()
                print('Connected to PostgreSQL.')
                return
        except Exception as e:
            print(e)

        time.sleep(0.5)
        print('Connection to PostgreSQL failed, retrying...')


if __name__ == '__main__':
    wait_for_db()
