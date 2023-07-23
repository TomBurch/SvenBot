import requests

from SvenBot.commands.command_models import *
from SvenBot.config import APP_URL, DEFAULT_HEADERS

url = f"{APP_URL}/guilds/333316787603243018/commands"

update = []

commands = [
    members,
    myroles,
    role,
    roles
]

if __name__ == "__main__":
    for command in commands:
        if command["name"] in update:
            r = requests.post(url, headers=DEFAULT_HEADERS, json=command.dict())
            print(r.status_code, r.reason, r.text)
