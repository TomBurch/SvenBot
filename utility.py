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