import os
import requests

from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")

url = f"https://discord.com/api/v8/applications/{CLIENT_ID}/guilds/342006395010547712/commands"

class ApplicationCommandOptionType:
    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8

headers = {
    "Authorization": f"Bot {BOT_TOKEN}"
}

ping_json = {
    "name": "ping",
    "description": "Ping!"
}

role_json = {
    "name": "role",
    "description": "Join or leave a role",
    "options": [{
        "name": "role",
        "description": "The role",
        "type": ApplicationCommandOptionType.ROLE,
        "required": True,
    }]
}

if __name__ == "__main__":
    r = requests.post(url, headers = headers, json = role_json)
    print(r.status_code, r.reason, r.text)
    None
