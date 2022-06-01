import logging
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from starlette.status import HTTP_200_OK

from SvenBot import config
from SvenBot.models import InteractionResponseType, ResponseData, Response

gunicorn_logger = logging.getLogger('gunicorn.error')

ARCHUB_TOKEN = config.settings.ARCHUB_TOKEN
BOT_TOKEN = config.settings.BOT_TOKEN
CLIENT_ID = config.settings.CLIENT_ID
PUBLIC_KEY = config.settings.PUBLIC_KEY
GITHUB_TOKEN = config.settings.GITHUB_TOKEN

TEST_CHANNEL = config.settings.TEST_CHANNEL
STAFF_CHANNEL = config.settings.STAFF_CHANNEL

ADMIN_ROLE = config.settings.ADMIN_ROLE

ARCHUB_URL = "https://arcomm.co.uk/api/v1"
APP_URL = f"https://discord.com/api/v8/applications/{CLIENT_ID}"
CHANNELS_URL = "https://discord.com/api/v8/channels"
GUILD_URL = "https://discord.com/api/v8/guilds"
REPO_URL = "https://events.arcomm.co.uk/api"

DEFAULT_HEADERS = {
    "Authorization": f"Bot {BOT_TOKEN}"
}

ARCHUB_HEADERS = {
    "Authorization": f"Bearer {ARCHUB_TOKEN}"
}

GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}"
}


async def req(function, statuses, url, params=None, json=None, headers=DEFAULT_HEADERS):
    if json is not None:
        r = await function(url, headers=headers, params=params, json=json)
    else:
        r = await function(url, headers=headers, params=params)

    if r.status_code not in statuses:
        gunicorn_logger.error(f"Received unexpected status code {r.status_code} (expected {statuses})\n{r.text}")
        raise RuntimeError(f"Req error: {r.text}")
    return r


async def get(statuses, url, params=None):
    async with httpx.AsyncClient() as client:
        return await req(client.get, statuses, url, params)


async def delete(statuses, url, params=None):
    async with httpx.AsyncClient() as client:
        return await req(client.delete, statuses, url, params)


async def put(statuses, url, params=None):
    async with httpx.AsyncClient() as client:
        return await req(client.put, statuses, url, params)


async def post(statuses, url, params=None, json=None, headers=DEFAULT_HEADERS):
    async with httpx.AsyncClient() as client:
        return await req(client.post, statuses, url, params, json, headers)


async def patch(statuses, url, params=None, json=None):
    async with httpx.AsyncClient() as client:
        return await req(client.patch, statuses, url, params, json)


async def sendMessage(channel_id, message, mentions=[]):
    url = f"{CHANNELS_URL}/{channel_id}/messages"
    message = ResponseData(content=message, allowed_mentions={"parse": mentions})
    async with httpx.AsyncClient() as client:
        await req(client.post, [HTTP_200_OK], url, json=message.dict())

    return message


def ImmediateReply(content, mentions=[], ephemeral=False):
    data = ResponseData(content=content, allowed_mentions={"parse": mentions})
    if ephemeral:
        data.flags = 64

    return Response(type=InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE, data=data)


def basicValidation(role, botPosition):
    return role.get("tags", {}).get("bot_id") is None and role["position"] < botPosition


def colourValidation(role, botPosition):
    return basicValidation(role, botPosition) and role["color"] == 0


role_validate_funcs = {
    "342006395010547712": colourValidation,
    "240160552867987475": colourValidation,
    "333316787603243018": basicValidation
}


async def validateRole(guild_id, role, roles=None):
    if roles is None:
        roles = await getRoles(guild_id)

    botPosition = -1
    for r in roles:
        if r.get("tags", {}).get("bot_id") is not None:
            if r["tags"]["bot_id"] == CLIENT_ID:
                botPosition = r["position"]
                break

    if botPosition == -1:
        raise RuntimeError("Unable to find bot's role")

    role_validate = role_validate_funcs.get(guild_id)
    if role_validate is None:
        return False
    else:
        return role_validate(role, botPosition)


async def validateRoleById(guild_id, role_id):
    roleMatchingRoleId = None
    roles = await getRoles(guild_id)
    for r in roles:
        if r["id"] == role_id:
            roleMatchingRoleId = r
            break

    if roleMatchingRoleId is None:
        raise RuntimeError("Unable to find role")

    return await validateRole(guild_id, roleMatchingRoleId, roles)


async def getRoles(guild_id):
    url = f"{GUILD_URL}/{guild_id}/roles"
    roles = await get([200], url)
    return roles.json()


async def findRoleByName(guild_id, query, autocomplete=False, excludeReserved=True):
    query = query.lower()
    roles = await getRoles(guild_id)
    candidate = None

    for role in roles:
        roleName = role["name"].lower()
        if roleName == query:
            candidate = role
            break

        if autocomplete and re.match(re.escape(query), roleName):
            candidate = role

    if excludeReserved and (candidate is not None):
        if await validateRole(guild_id, candidate, roles):
            return candidate
        return None

    return candidate


def timeUntilOptime(modifier=0):
    today = datetime.now(tz=ZoneInfo('Europe/London'))
    opday = today
    opday = opday.replace(hour=18, minute=0, second=0) + timedelta(hours=modifier)
    if today > opday:
        opday = opday + timedelta(days=1)

    return opday - today
