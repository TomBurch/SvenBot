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


async def execute_role(interaction: Interaction):
    guild_id = interaction.guild_id
    user_id = interaction.member.user.id
    role_id, = interaction.data.options

    if not await utility.validateRoleById(guild_id, role_id.value):
        return f"<@&{role_id.value}> is restricted"

    url = f"{GUILD_URL}/{guild_id}/members/{user_id}/roles/{role_id.value}"

    if role_id.value in interaction.member.roles:
        r = await utility.delete([HTTP_204_NO_CONTENT, HTTP_403_FORBIDDEN], url)
        reply = f"You've left <@&{role_id.value}>"
    else:
        r = await utility.put([HTTP_204_NO_CONTENT, HTTP_403_FORBIDDEN], url)
        reply = f"You've joined <@&{role_id.value}>"

    if r.status_code == HTTP_403_FORBIDDEN:
        return f"<@&{role_id.value}> is restricted"
    return reply


async def execute_roles(interaction: Interaction):
    guild_id = interaction.guild_id
    roles = await utility.getRoles(guild_id)

    joinableRoles = []
    for role in roles:
        if await utility.validateRole(guild_id, role, roles):
            joinableRoles.append(role["name"])

    joinableRoles = sorted(joinableRoles)
    return "```\n{}\n```".format("\n".join(joinableRoles))


async def execute_members(interaction: Interaction):
    guild_id = interaction.guild_id
    role_id, = interaction.data.options

    url = f"{GUILD_URL}/{guild_id}/members"

    r = await utility.get([HTTP_200_OK], url, params={"limit": 200})
    members = r.json()
    reply = ""

    for member in members:
        if role_id.value in member["roles"]:
            reply += member["user"]["username"] + "\n"

    return f"```\n{reply}```"


async def execute_myroles(interaction: Interaction):
    reply = ""

    for role_id in interaction.member.roles:
        reply += f"<@&{role_id}>\n"

    return reply


async def execute_optime(interaction):
    today = datetime.now(tz=timezone('Europe/London'))
    if interaction.data.options is not None and len(interaction.data.options) > 0:
        modifier = interaction.data.options[0].value
    else:
        modifier = 0

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


async def execute_addrole(interaction: Interaction):
    guild_id = interaction.guild_id
    name, = interaction.data.options

    existingRole = await utility.findRoleByName(guild_id, name.value, excludeReserved=False)
    if existingRole is not None:
        role_id = existingRole["id"]
        return f"<@&{role_id}> already exists"

    url = f"{GUILD_URL}/{guild_id}/roles"
    r = await utility.post([HTTP_200_OK], url, json={"name": name.value, "mentionable": True})
    role_id = r.json()["id"]

    return f"<@&{role_id}> added"


async def execute_removerole(interaction: Interaction):
    guild_id = interaction.guild_id
    role_id, = interaction.data.options

    if await utility.validateRoleById(guild_id, role_id.value):
        url = f"{GUILD_URL}/{guild_id}/roles/{role_id.value}"

        await utility.delete([HTTP_204_NO_CONTENT], url)
        return "Role deleted"
    else:
        return "Role is restricted"


async def execute_subscribe(interaction: Interaction):
    user_id = interaction.member.user.id
    mission_id, = interaction.data.options
    url = f"{ARCHUB_URL}/missions/{mission_id.value}/subscribe?discord_id={user_id}"
    r = await utility.post([HTTP_201_CREATED, HTTP_204_NO_CONTENT], url, headers=ARCHUB_HEADERS)
    missionUrl = f"https://arcomm.co.uk/hub/missions/{mission_id.value}"

    if r.status_code == HTTP_201_CREATED:
        return f"You are now subscribed to {missionUrl}"

    return f"You are no longer subscribed to {missionUrl}"


async def execute_ticket(interaction: Interaction):
    member = interaction.member
    repo, title, body = interaction.data.options
    username = member.user.username if (member.nick is None) else member.nick
    json = {"title": f"{username}: {title.value}",
            "body": body.value}

    repoUrl = f"https://api.github.com/repos/{repo.value}/issues"
    r = await utility.post([HTTP_201_CREATED], repoUrl, json=json, headers=GITHUB_HEADERS)
    createdUrl = r.json()["html_url"]

    return f"Ticket created at: {createdUrl}"


async def execute_cointoss(interaction: Interaction):
    return random.choice(["Heads", "Tails"])


async def execute_renamerole(interaction: Interaction):
    guild_id = interaction.guild_id
    role_id, new_name = interaction.data.options
    if not await utility.validateRoleById(guild_id, role_id.value):
        return f"<@&{role_id.value}> is restricted"

    existingRole = await utility.findRoleByName(guild_id, new_name.value, excludeReserved=False)
    if existingRole is not None:
        role_id = existingRole["id"]
        return f"<@&{role_id}> already exists"

    url = f"{GUILD_URL}/{guild_id}/roles/{role_id.value}"
    await utility.patch([HTTP_200_OK], url, json={"name": new_name.value})

    return f"<@&{role_id.value}> was renamed"


async def execute_ping(interaction: Interaction):
    return "Pong!"


execute_map = {
    "addrole": execute_addrole,
    "cointoss": execute_cointoss,
    "members": execute_members,
    "myroles": execute_myroles,
    "optime": execute_optime,
    "ping": execute_ping,
    "removerole": execute_removerole,
    "renamerole": execute_renamerole,
    "role": execute_role,
    "roles": execute_roles,
    "subscribe": execute_subscribe,
    "ticket": execute_ticket,
}

ephemeral = ["myroles"]


async def handle_interaction(interaction: Interaction):
    if interaction.type != InteractionType.APPLICATION_COMMAND:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Not an application command")

    command = interaction.data.name
    if command not in execute_map:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail=f"'{command}' is not a known command")

    try:
        gunicorn_logger.info(f"'{interaction.member.user.username}' executing '{command}'")

        reply = await execute_map[command](interaction)
        return utility.ImmediateReply(reply, ephemeral=command in ephemeral)

    except Exception as e:
        gunicorn_logger.error(f"Error executing '{command}':\n{str(e)})")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error executing '{command}'")


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
