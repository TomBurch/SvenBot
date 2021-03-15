import requests

from command_utility import ApplicationCommandOptionType, APP_URL, HEADERS

url = f"{APP_URL}/guilds/333316787603243018/commands"

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

roles_json = {
    "name": "role",
    "description": "Get a list of roles you can join"
}

members_json = {
    "name": "members",
    "description": "Get a list of members in a role",
    "options": [{
        "name": "role",
        "description": "The role",
        "type": ApplicationCommandOptionType.ROLE,
        "required": True,
    }]
}

myroles_json = {
    "name": "myroles",
    "description": "Get a list of roles you're in"
}

if __name__ == "__main__":
    #r = requests.post(url, headers = HEADERS, json = role_json)
    #r = requests.delete(f"{url}/818978868785709066", headers = HEADERS)
    #r = requests.get(url, headers = HEADERS)
    print(r.status_code, r.reason, r.text)