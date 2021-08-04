import logging
import re

import httpx

import config
from models import InteractionResponseType, Response, ResponseData

gunicorn_logger = logging.getLogger('gunicorn.error')

ARCHUB_TOKEN = config.settings.ARCHUB_TOKEN
BOT_TOKEN = config.settings.BOT_TOKEN
CLIENT_ID = config.settings.CLIENT_ID
PUBLIC_KEY = config.settings.PUBLIC_KEY
GITHUB_TOKEN = config.settings.GITHUB_TOKEN

ARCHUB_URL = "https://arcomm.co.uk/api/v1"
GUILD_URL = "https://discord.com/api/v8/guilds"
CHANNELS_URL = "https://discord.com/api/v8/channels"
APP_URL = f"https://discord.com/api/v8/applications/{CLIENT_ID}"

ARCHUB_CHANNEL = 703618484386398349

DEFAULT_HEADERS = {
    "Authorization": f"Bot {BOT_TOKEN}"
}

ARCHUB_HEADERS = {
    "Authorization": f"Bearer {ARCHUB_TOKEN}"
}

GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}"
}

async def req(function, statuses, url, params = None, json = None, headers = DEFAULT_HEADERS):
    if json is not None:
        r = await function(url, headers = headers, params = params, json = json)
    else:
        r = await function(url, headers = headers, params = params)

    if r.status_code not in statuses:
        gunicorn_logger.error(f"Received unexpected status code {r.status_code} (expected {statuses})\n{r.text}")
        raise RuntimeError(f"Req error: {r.text}")
    return r

async def get(statuses, url, params = None):
    async with httpx.AsyncClient() as client:
        return await req(client.get, statuses, url, params)

async def delete(statuses, url, params = None):
    async with httpx.AsyncClient() as client:
        return await req(client.delete, statuses, url, params)

async def put(statuses, url, params = None):
    async with httpx.AsyncClient() as client:
        return await req(client.put, statuses, url, params)

async def post(statuses, url, params = None, json = None, headers = DEFAULT_HEADERS):
    async with httpx.AsyncClient() as client:
        return await req(client.post, statuses, url, params, json, headers)

async def sendMessage(channel_id, message):
    url = f"{CHANNELS_URL}/{channel_id}/messages"
    json = {"content": message}
    async with httpx.AsyncClient() as client:
        return await req(client.post, [200], url, json = json)

def ImmediateReply(content, mentions = [], ephemeral = False):
    data = ResponseData(content = content, allowed_mentions = {"parse": mentions})
    if ephemeral:
        data.flags = 64
    
    return Response(type = InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE, data = data)

def basicValidation(role, botPosition):
    return role.get("tags", {}).get("bot_id") is None and role["position"] < botPosition

def colourValidation(role, botPosition):
    return basicValidation(role, botPosition) and role["color"] == 0 

role_validate_funcs = {
    "342006395010547712": colourValidation,
    "240160552867987475": colourValidation,
    "333316787603243018": basicValidation
}

async def validateRole(guild_id, role, roles = None):
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

async def findRole(guild_id, query, autocomplete = False):
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

    if candidate is not None:
        if await validateRole(guild_id, candidate, roles):
            gunicorn_logger.info(candidate["name"] + " is reserved")
            return candidate
    
    return None
