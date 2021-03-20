import logging
import os
import requests

from dotenv import load_dotenv
from discord_interactions import InteractionResponseType

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

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
    return basicValidation(role, botPosition) and role.get("colour") != 0 

role_validate_funcs = {
    "342006395010547712": colourValidation,
    "333316787603243018": basicValidation
}

def validateRole(guild_id, role, botPosition):
    role_validate = role_validate_funcs.get(guild_id)
    if role_validate is None:
        return False
    else:
        return role_validate(role, botPosition)