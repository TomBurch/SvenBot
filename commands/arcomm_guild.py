import os
import requests

from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("APP_ID")

url = f"https://discord.com/api/v8/applications/{CLIENT_ID}/guilds/342006395010547712/commands"

headers = {
    "Authorization": f"Bot {BOT_TOKEN}"
}

ping_json = {
    "name": "ping",
    "description": "Ping!"
}

if __name__ == "__main__":
    r = requests.post(url, headers = headers, json = ping_json)
    print(r.status_code, r.reason)
    None
