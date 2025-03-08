import requests

from SvenBot.commands.command_models import (
    addrole,
    d20,
    members,
    myroles,
    optime,
    removerole,
    role,
    roles,
)
from SvenBot.config import APP_URL, DEFAULT_HEADERS

url = f"{APP_URL}/guilds/342006395010547712/commands"
STAFF_ROLE_ID = 365987804519333888

update = []
staff = ["addrole", "removerole"]

commands = [
    addrole,
    d20,
    removerole,
    members,
    myroles,
    optime,
    role,
    roles,
]

if __name__ == "__main__":
    r = requests.get(url, headers=DEFAULT_HEADERS)
    print(r.status_code, r.reason, r.text)
    current_commands = r.json()

    for command in commands:
        command_id = next((c["id"] for c in current_commands if c["name"] == command.name), None)
        print("===================")
        print(command.name)
        print(f"command_id = {command_id}")

        if command.name in update:
            print("update queued")
            r = requests.post(url, headers=DEFAULT_HEADERS, json=command.dict())
            print(r.status_code, r.reason, r.text)

            if command.name in staff:
                if command_id is not None:
                    print("adding staff permissions")
                    permissions = {
                        "permissions": [
                            {
                                "id": STAFF_ROLE_ID,
                                "type": 1,
                                "permission": True,
                            },
                        ],
                    }
                    r = requests.put(f"{url}/{command_id}/permissions", headers=DEFAULT_HEADERS, json=permissions)
                    print(r.status_code, r.reason, r.text)
                else:
                    print("ERROR command_id is NONE")
