import time
from common.src.theatre.core.config import G_API_PATH_SETTINGS
import httpx
from httpx import Response


def wait_for_payment_api():
    while True:
        try:
            response: Response = httpx.get(G_API_PATH_SETTINGS.payment_api_path)
            if response.status_code == 404:
                return
        except Exception as e:
            print(e)

        time.sleep(1)
        print('Connection to PaymentAPI failed, retrying...')


if __name__ == '__main__':
    wait_for_payment_api()
