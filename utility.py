import logging
import os
import re

import httpx
from dotenv import load_dotenv
from nacl.signing import VerifyKey
from fastapi import HTTPException
from google.cloud import datastore

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
PUBLIC_KEY = os.getenv("PUBLIC_KEY")

GUILD_URL = "https://discord.com/api/v8/guilds"
CHANNELS_URL = "https://discord.com/api/v8/channels"

ARCHUB_CHANNEL = 703618484386398349

DATASTORE = datastore.Client.from_service_account_json("gcs.json")

class InteractionType:
    PING = 1
    APPLICATION_COMMAND = 2

class InteractionResponseType:
    PONG = 1
    CHANNEL_MESSAGE_WITH_SOURCE = 4
    DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5

async def verify_request(request):
    signature = request.headers.get("X-Signature-Ed25519")
    timestamp = request.headers.get("X-Signature-Timestamp")
    body = await request.body()
    if signature is None or timestamp is None or not verify_key(body, signature, timestamp):
        raise HTTPException(status_code = 401, detail = "Bad request signature")

def verify_key(body, signature, timestamp):
    message = timestamp.encode() + body

    try:
        VerifyKey(bytes.fromhex(PUBLIC_KEY)).verify(message, bytes.fromhex(signature))
        return True
    except Exception as e:
        logging.error(e)
        return False

DEFAULT_HEADERS = {
    "Authorization": f"Bot {BOT_TOKEN}"
}

async def req(function, statuses, url, params = None, json = None):
    if json is not None:
        r = await function(url, headers = DEFAULT_HEADERS, params = params, json = json)
    else:
        r = await function(url, headers = DEFAULT_HEADERS, params = params)

    if r.status_code not in statuses:
        logging.error(f"Received unexpected status code {r.status_code} (expected {statuses})\n{r.text}")
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

async def post(statuses, url, params = None, json = None):
    async with httpx.AsyncClient() as client:
        return await req(client.post, statuses, url, params, json)

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
            logging.info(candidate["name"] + " is reserved")
            return candidate
    
    return None

async def getDiscordId(steamId):
    query = DATASTORE.query(kind = "DiscordIdentifier")
    query.add_filter("SteamID", "=", steamId)
    results = list(query.fetch(limit = 1))
    discordId = results[0]["DiscordID"] if len(results) > 0 else None
    return discordId