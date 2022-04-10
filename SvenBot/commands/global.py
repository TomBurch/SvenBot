import requests

from SvenBot.utility import DEFAULT_HEADERS, APP_URL

url = f"{APP_URL}/commands"

if __name__ == "__main__":
    # r = requests.post(url, headers = HEADERS, json = ping.dict())
    # r = requests.delete(f"{url}/818978868785709066", headers = HEADERS)
    r = requests.get(url, headers=DEFAULT_HEADERS)
    print(r.status_code, r.reason, r.text)
