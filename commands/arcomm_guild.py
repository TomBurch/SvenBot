import requests

from command_utility import ApplicationCommandOptionType, APP_URL, HEADERS

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
            "type": ApplicationCommandOptionType.STRING,
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
            "type": ApplicationCommandOptionType.ROLE,
            "required": True, 
        }]
    },
    {
        "name": "members",
        "description": "Get a list of members in a role",
        "options": [{
            "name": "role",
            "description": "The role",
            "type": ApplicationCommandOptionType.ROLE,
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
            "type": ApplicationCommandOptionType.INTEGER,
            "required": False,
        }]
    },
    {
        "name": "role",
        "description": "Join or leave a role",
        "options": [{
            "name": "role",
            "description": "The role",
            "type": ApplicationCommandOptionType.ROLE,
            "required": True,
        }]
    },
    {
        "name": "roles",
        "description": "Get a list of roles you can join"
    },
]

if __name__ == "__main__":
    r = requests.get(url, headers = HEADERS)
    print(r.status_code, r.reason, r.text)
    currentCommands = r.json()

    for command in commands:
        commandId = next((c["id"] for c in currentCommands if c["name"] == command["name"]), None)
        print("===================")
        print(command["name"])
        print(f"commandId = {commandId}")

        if command["name"] in update:
            print("update queued")
            r = requests.post(url, headers = HEADERS, json = command)
            print(r.status_code, r.reason, r.text)

            if command["name"] in staff:
                if commandId is not None:
                    print("adding staff permisions")
                    permissions = {
                        "permissions": [{
                                "id": STAFF_ROLE_ID,
                                "type": 1,
                                "permission": True
                            }]
                    }
                    r = requests.put(f"{url}/{commandId}/permissions", headers = HEADERS, json = permissions)
                    print(r.status_code, r.reason, r.text)
                else:
                    print("ERROR commandId is NONE")