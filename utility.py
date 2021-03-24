import logging
import os
import cachetools.func

import httpx
from dotenv import load_dotenv
from nacl.encoding import HexEncoder
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from sanic.exceptions import abort

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
PUBLIC_KEY = os.getenv("PUBLIC_KEY")

class InteractionType:
    PING = 1
    APPLICATION_COMMAND = 2

class InteractionResponseType:
    PONG = 1
    CHANNEL_MESSAGE_WITH_SOURCE = 4
    DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5

def verify_request(request):
    signature = request.headers.get("X-Signature-Ed25519")
    timestamp = request.headers.get("X-Signature-Timestamp")
    if signature is None or timestamp is None or not verify_key(request.body, signature, timestamp):
        abort(401, "Bad request signature")

def verify_key(body, signature, timestamp):
    message = timestamp.encode() + body

    try:
        VerifyKey(bytes.fromhex(PUBLIC_KEY)).verify(message, bytes.fromhex(signature))
        return True
    except Exception as e:
        logging.error(e)
        return False

headers = {
    "Authorization": f"Bot {BOT_TOKEN}"
}

async def req(function, statuses, url, params = None):
    r = await function(url, headers = headers, params = params)
    if r.status_code not in statuses:
        logging.error(f"Received unexpected status code {r.status_code} (expected {statuses})\n{r.reason}\n{r.text}")
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

class Reply(dict):
    def __init__(self, _type, content, mentions = None, ephemeral = False):
        data = {"content": content}
        if mentions is not None:
            data["allowed_mentions"] = {"parse": mentions}
        if ephemeral:
            data["flags"] = 64

        dict.__init__(self, type = _type, data = data)

class ImmediateReply(Reply):
    def __init__(self, content, mentions = None, ephemeral = False):
        super().__init__(InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE, content, mentions, ephemeral)

def basicValidation(role, botPosition):
    return role.get("tags", {}).get("bot_id") is None and role["position"] < botPosition

def colourValidation(role, botPosition):
    return basicValidation(role, botPosition) and role["color"] == 0 

role_validate_funcs = {
    "342006395010547712": colourValidation,
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

@cachetools.func.ttl_cache(ttl = 40)
async def getRoles(guild_id):
    url = f"https://discord.com/api/v8/guilds/{guild_id}/roles"
    roles = await get([200], url)
    return roles.json()

def clearMemoizeCache():
    getRoles.cache_clear()
