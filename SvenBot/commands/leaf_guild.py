import requests

from SvenBot.models import OptionType
from SvenBot.utility import APP_URL, DEFAULT_HEADERS

url = f"{APP_URL}/guilds/333316787603243018/commands"

update = []

commands = [
    {
        "name": "members",
        "description": "Get a list of members in a role",
        "options": [{
            "name": "role",
            "description": "The role",
            "type": OptionType.ROLE,
            "required": True,
        }]
    },
    {
        "name": "myroles",
        "description": "Get a list of roles you're in"
    },
    {
        "name": "role",
        "description": "Join or leave a role",
        "options": [{
            "name": "role",
            "description": "The role",
            "type": OptionType.ROLE,
            "required": True,
        }]
    },
    {
        "name": "roles",
        "description": "Get a list of roles you can join"
    },
]

if __name__ == "__main__":
    for command in commands:
        if command["name"] in update:
            r = requests.post(url, headers = DEFAULT_HEADERS, json = command)
            print(r.status_code, r.reason, r.text)