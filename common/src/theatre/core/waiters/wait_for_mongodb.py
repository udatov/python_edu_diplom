import time
from common.src.theatre.core.config import G_MONGODB_SETTINGS
from pymongo import MongoClient
from pymongo.errors import PyMongoError


def wait_for_mongodb():
    while True:
        try:
            client = MongoClient(G_MONGODB_SETTINGS.conn_string, connect=True)
            print(f'Mongodb server_info={client.server_info()}')
            print('Connected to Mongo.')
            return
        except PyMongoError as e:
            print(f"Mongodb exception: {e}")
        except Exception as e:
            print(f"Error connecting to Mongodb: {e}")

        time.sleep(1)
        print('Connection to Mongodb failed, retrying...')


if __name__ == '__main__':
    wait_for_mongodb()
