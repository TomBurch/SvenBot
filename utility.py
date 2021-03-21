import logging
import os
import requests

from dotenv import load_dotenv
from flask import Flask
from flask_caching import Cache
from discord_interactions import InteractionResponseType

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")

cache = Cache(config = {'CACHE_TYPE': 'SimpleCache'})
app = Flask(__name__)
cache.init_app(app)

headers = {
    "Authorization": f"Bot {BOT_TOKEN}"
}

def req(function, statuses, url, params = None):
    r = function(url, headers = headers, params = params)
    if r.status_code not in statuses:
        logging.error(f"Received unexpected status code {r.status_code} (expected {statuses})\n{r.reason}\n{r.text}")
        raise RuntimeError(f"Req error: {r.text}")
    return r

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

def validateRole(guild_id, role):
    botPosition = -1
    for r in getRoles(guild_id):
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

def validateRoleById(guild_id, role_id):
    roleMatchingRoleId = None
    for r in getRoles(guild_id):
        if r["id"] == role_id:
            roleMatchingRoleId = r
            break
    
    if roleMatchingRoleId is None:
        raise RuntimeError("Unable to find role")

    return validateRole(guild_id, roleMatchingRoleId)

@cache.memoize(40)
def getRoles(guild_id):
    url = f"https://discord.com/api/v8/guilds/{guild_id}/roles"
    return req(requests.get, [200], url).json()

def clearMemoizeCache():
    cache.delete_memoized(getRoles)
