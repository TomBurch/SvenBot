from utility import APP_URL, DEFAULT_HEADERS
import requests

url = f"{APP_URL}/commands"

ping_json = {
    "name": "ping",
    "description": "Ping!"
}

if __name__ == "__main__":
    #r = requests.post(url, headers = HEADERS, json = ping_json)
    #r = requests.delete(f"{url}/818978868785709066", headers = HEADERS)
    r = requests.get(url, headers = DEFAULT_HEADERS)
    print(r.status_code, r.reason, r.text)