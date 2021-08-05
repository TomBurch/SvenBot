import requests

from SvenBot.models import OptionType
from SvenBot.utility import APP_URL, DEFAULT_HEADERS

url = f"{APP_URL}/guilds/240160552867987475/commands"
STAFF_ROLE_ID = 324227354329219072

update = []
staff = ["addrole", "removerole"]

commands = [
    {
        "name": "addrole",
        "description": "Add a new role",
        "default_permission": False,
        "options": [{
            "name": "name",
            "description": "Name",
            "type": OptionType.STRING,
            "required": True, 
        }]
    },
    {
        "name": "removerole",
        "description": "Remove an existing role",
        "default_permission": False,
        "options": [{
            "name": "role",
            "description": "Role",
            "type": OptionType.ROLE,
            "required": True, 
        }]
    },
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
        "name": "optime",
        "description": "Time until optime",
        "options": [{
            "name": "modifier",
            "description": "Modifier",
            "type": OptionType.INTEGER,
            "required": False,
        }]
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
    {
        "name": "subscribe",
        "description": "(Un)subscribe to mission notifications",
        "options": [{
            "name": "mission",
            "description": "The mission ID",
            "type": OptionType.INTEGER,
            "required": True,
        }]
    },
    {
        "name": "ticket",
        "description": "Create a github ticket",
        "options": [{
            "name": "repo",
            "description": "Target repo",
            "type": OptionType.STRING,
            "required": True,
            "choices": [
                {
                    "name": "archub",
                    "value": "ARCOMM/ARCHUB"
                },
                {
                    "name": "arc_misc",
                    "value": "ARCOMM/arc_misc"
                },
                {
                    "name": "arcmt",
                    "value": "ARCOMM/ARCMT"
                },
                {
                    "name": "svenbot",
                    "value": "TomBurch/SvenBot"
                }
            ]
            },
            {
                "name": "title",
                "description": "Ticket title",
                "type": OptionType.STRING,
                "required": True,
            },
            {
                "name": "body",
                "description": "Ticket description",
                "type": OptionType.STRING,
                "required": True,
            }
        ]
    }
]

if __name__ == "__main__":
    r = requests.get(url, headers = DEFAULT_HEADERS)
    print(r.status_code, r.reason, r.text)
    currentCommands = r.json()

    for command in commands:
        commandId = next((c["id"] for c in currentCommands if c["name"] == command["name"]), None)
        print("===================")
        print(command["name"])
        print(f"commandId = {commandId}")

        if command["name"] in update:
            print("update queued")
            r = requests.post(url, headers = DEFAULT_HEADERS, json = command)
            print(r.status_code, r.reason, r.text)

            if command["name"] in staff:
                if commandId is not None:
                    print("adding staff permissions")
                    permissions = {
                        "permissions": [{
                                "id": STAFF_ROLE_ID,
                                "type": 1,
                                "permission": True
                            }]
                    }
                    r = requests.put(f"{url}/{commandId}/permissions", headers = DEFAULT_HEADERS, json = permissions)
                    print(r.status_code, r.reason, r.text)
                else:
                    print("ERROR commandId is NONE")
