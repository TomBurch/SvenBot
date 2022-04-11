import logging
import os
import random
import sys
from datetime import datetime, timedelta

import uvicorn
from fastapi import FastAPI, Body, Request, HTTPException
from fastapi.params import Depends
from nacl.signing import VerifyKey
from pytz import timezone
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST, \
    HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_501_NOT_IMPLEMENTED

PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

from SvenBot import utility
from SvenBot.models import InteractionType, Response, Interaction, InteractionResponseType
from SvenBot.utility import GUILD_URL, ARCHUB_URL, ARCHUB_HEADERS, PUBLIC_KEY, GITHUB_HEADERS

gunicorn_logger = logging.getLogger('gunicorn.error')


async def execute_role(roles, role_id, guild_id, user_id):
    if not await utility.validateRoleById(guild_id, role_id):
        gunicorn_logger.warning(f"Role <@&{role_id}> is restricted (validation)")
        return f"<@{user_id}> Role <@&{role_id}> is restricted"

    url = f"{GUILD_URL}/{guild_id}/members/{user_id}/roles/{role_id}"

    if role_id in roles:
        r = await utility.delete([HTTP_204_NO_CONTENT, HTTP_403_FORBIDDEN], url)
        reply = f"<@{user_id}> You've left <@&{role_id}>"
    else:
        r = await utility.put([HTTP_204_NO_CONTENT, HTTP_403_FORBIDDEN], url)
        reply = f"<@{user_id}> You've joined <@&{role_id}>"

    if r.status_code == 403:
        gunicorn_logger.warning(f"Role <@&{role_id}> is restricted (403)")
        return f"<@{user_id}> Role <@&{role_id}> is restricted"

    return reply


async def execute_roles(guild_id):
    roles = await utility.getRoles(guild_id)

    joinableRoles = []
    for role in roles:
        if await utility.validateRole(guild_id, role, roles):
            joinableRoles.append(role["name"])

    joinableRoles = sorted(joinableRoles)
    return "```\n{}\n```".format("\n".join(joinableRoles))


async def execute_members(role_id, guild_id):
    url = f"{GUILD_URL}/{guild_id}/members"

    r = await utility.get([HTTP_200_OK], url, params={"limit": 200})
    members = r.json()
    reply = ""

    for member in members:
        if role_id in member["roles"]:
            reply += member["user"]["username"] + "\n"

    return f"```\n{reply}```"


def execute_myroles(roles):
    reply = ""

    for role_id in roles:
        reply += f"<@&{role_id}>\n"

    return reply


def execute_optime(today, modifier):
    try:
        opday = today
        opday = opday.replace(hour=18, minute=0, second=0) + timedelta(hours=modifier)
        if today > opday:
            opday = opday + timedelta(days=1)

        if modifier == 0:
            modifierString = ""
        elif modifier > 0:
            modifierString = f" +{modifier}"
        else:
            modifierString = f" {modifier}"

        timeUntilOptime = opday - today
        return f"Optime{modifierString} starts in {timeUntilOptime}!"
    except ValueError:
        return "Optime modifier is too large"


async def execute_addrole(guild_id, name):
    existingRole = await utility.findRoleByName(guild_id, name, excludeReserved=False)
    if existingRole is not None:
        role_id = existingRole["id"]
        return f"<@&{role_id}> already exists"

    url = f"{GUILD_URL}/{guild_id}/roles"
    r = await utility.post([HTTP_200_OK], url, json={"name": name, "mentionable": True})
    role_id = r.json()["id"]

    return f"<@&{role_id}> added"


async def execute_removerole(guild_id, role_id):
    if await utility.validateRoleById(guild_id, role_id):
        url = f"{GUILD_URL}/{guild_id}/roles/{role_id}"

        await utility.delete([HTTP_204_NO_CONTENT], url)
        return "Role deleted"
    else:
        return "Role is restricted"


async def execute_subscribe(user_id, mission_id):
    url = f"{ARCHUB_URL}/missions/{mission_id}/subscribe?discord_id={user_id}"
    r = await utility.post([HTTP_201_CREATED, HTTP_204_NO_CONTENT], url, headers=ARCHUB_HEADERS)
    missionUrl = f"https://arcomm.co.uk/hub/missions/{mission_id}"

    if r.status_code == HTTP_201_CREATED:
        return f"You are now subscribed to {missionUrl}"

    return f"You are no longer subscribed to {missionUrl}"


async def execute_ticket(repo, title, body, member):
    title = "{}: {}".format(member.user.username if (member.nick is None) else member.nick, title)
    json = {"title": title,
            "body": body}

    repoUrl = f"https://api.github.com/repos/{repo}/issues"
    r = await utility.post([HTTP_201_CREATED], repoUrl, json=json, headers=GITHUB_HEADERS)
    createdUrl = r.json()["html_url"]

    return f"Ticket created at: {createdUrl}"


def execute_cointoss():
    return random.choice(["Heads", "Tails"])


async def execute_renamerole(guild_id, role_id, new_name):
    if not await utility.validateRoleById(guild_id, role_id):
        return f"<@&{role_id}> is restricted"

    existingRole = await utility.findRoleByName(guild_id, new_name, excludeReserved=False)
    if existingRole is not None:
        role_id = existingRole["id"]
        return f"<@&{role_id}> already exists"

    url = f"{GUILD_URL}/{guild_id}/roles/{role_id}"
    await utility.patch([HTTP_200_OK], url, json={"name": new_name})

    return f"<@&{role_id}> was renamed"


async def handle_interaction(interaction):
    if interaction.type == InteractionType.APPLICATION_COMMAND:
        data = interaction.data
        command = data.name

        try:
            options = data.options
            member = interaction.member
            user = member.user
            username = user.username
            guild_id = interaction.guild_id

            gunicorn_logger.info(f"'{username}' executing '{command}'")

            if command == "ping":
                return utility.ImmediateReply("Pong!")

            elif command == "role":
                role_id = options[0].value
                reply = await execute_role(member.roles, role_id, guild_id, user.id)
                return utility.ImmediateReply(reply, mentions=["users"])

            elif command == "roles":
                reply = await execute_roles(guild_id)
                return utility.ImmediateReply(reply)

            elif command == "members":
                role_id = options[0].value
                reply = await execute_members(role_id, guild_id)
                return utility.ImmediateReply(reply)

            elif command == "myroles":
                reply = execute_myroles(member.roles)
                return utility.ImmediateReply(reply, ephemeral=True)

            elif command == "optime":
                if options is not None and len(options) > 0:
                    modifier = options[0].value
                else:
                    modifier = 0

                reply = execute_optime(datetime.now(tz=timezone('Europe/London')), modifier)
                return utility.ImmediateReply(reply)

            elif command == "addrole":
                name = options[0].value
                reply = await execute_addrole(guild_id, name)
                return utility.ImmediateReply(reply)

            elif command == "removerole":
                role_id = options[0].value
                reply = await execute_removerole(guild_id, role_id)
                return utility.ImmediateReply(reply)

            elif command == "subscribe":
                mission_id = options[0].value
                reply = await execute_subscribe(user.id, mission_id)
                return utility.ImmediateReply(reply)

            elif command == "ticket":
                repo = options[0].value
                title = options[1].value
                body = options[2].value
                reply = await execute_ticket(repo, title, body, member)
                return utility.ImmediateReply(reply)

            elif command == "cointoss":
                reply = execute_cointoss()
                return utility.ImmediateReply(reply)

            elif command == "renamerole":
                role_id = options[0].value
                new_name = options[1].value
                reply = await execute_renamerole(guild_id, role_id, new_name)
                return utility.ImmediateReply(reply)

        except Exception as e:
            gunicorn_logger.error(f"Error executing '{command}':\n{str(e)})")
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error executing '{command}'")

        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail=f"'{command}' is not a known command")
    else:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Not an application command")


class ValidDiscordRequest:
    async def __call__(self, request: Request):
        signature = request.headers.get("X-Signature-Ed25519")
        timestamp = request.headers.get("X-Signature-Timestamp")
        body = await request.body()

        if signature is None or timestamp is None or not verify_key(body, signature, timestamp):
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Bad request signature")

        return True


def verify_key(body, signature, timestamp):
    message = timestamp.encode() + body

    try:
        VerifyKey(bytes.fromhex(PUBLIC_KEY)).verify(message, bytes.fromhex(signature))
        return True
    except Exception as e:
        gunicorn_logger.error(e)
        return False


def app():
    fast_app = FastAPI()

    @fast_app.post('/interaction/', response_model=Response)
    async def interact(interaction: Interaction = Body(...), valid: bool = Depends(ValidDiscordRequest())):
        if interaction.type == InteractionType.PING:
            return Response(type=InteractionResponseType.PONG)

        response = await handle_interaction(interaction)
        return response

    @fast_app.get('/abc/')
    def hello_world():
        return {"message", "Hello, World!"}

    return fast_app


app = app()

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)
