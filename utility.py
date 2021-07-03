from enum import IntEnum
import logging
import os
import re
from typing import Any, Optional
from fastapi.openapi.models import Discriminator

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel

gunicorn_logger = logging.getLogger('gunicorn.error')

load_dotenv()
ARCHUB_TOKEN = os.getenv("ARCHUB_TOKEN")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
PUBLIC_KEY = os.getenv("PUBLIC_KEY")

ARCHUB_URL = "https://arcomm.co.uk/api/v1"
GUILD_URL = "https://discord.com/api/v8/guilds"
CHANNELS_URL = "https://discord.com/api/v8/channels"

ARCHUB_CHANNEL = 703618484386398349

class InteractionType(IntEnum):
    PING = 1
    APPLICATION_COMMAND = 2
    MESSAGE_COMPONENT = 3

class InteractionResponseType(IntEnum):
    PONG = 1
    CHANNEL_MESSAGE_WITH_SOURCE = 4
    DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5

class User(BaseModel):
    id: str
    username: str
    discriminator: str
    avatar: Any
    bot: Optional[bool]
    system: Any
    mfa_enabled: Any
    locale: Any
    verified: Any
    email: Any
    flags: Any
    premium_type: Any
    public_flags: Any

class Member(BaseModel):
    user: Optional[User]
    nick: Optional[str]
    roles: Any
    joined_at: Any
    premium_since: Any
    deaf: Any
    mute: Any
    pending: Any
    permissions: Optional[str]

class Command(BaseModel):
    id: str
    name: str
    resolved: Any
    options: Any
    custom_id: Any
    component_type: Any

class Interaction(BaseModel):
    id: str
    application_id: str
    type: InteractionType
    data: Command
    guild_id: Optional[str]
    channel_id: Optional[str]
    member: Optional[Member]
    user: Optional[User]
    token: str
    version: int
    message: Any

DEFAULT_HEADERS = {
    "Authorization": f"Bot {BOT_TOKEN}"
}

ARCHUB_HEADERS = {
    "Authorization": f"Bearer {ARCHUB_TOKEN}"
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

class Reply(dict):
    def __init__(self, _type, content, mentions = None, ephemeral = False):
        data = {"content": content}
        if mentions is not None:
            data["allowed_mentions"] = {"parse": mentions}
        if ephemeral:
            data["flags"] = 64

        dict.__init__(self, type = _type, data = data)

class ImmediateReply(Reply):
    def __init__(self, content, mentions = [], ephemeral = False):
        super().__init__(InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE, content, mentions, ephemeral)

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
