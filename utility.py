import logging
import os
import requests

from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

headers = {
    "Authorization": f"Bot {BOT_TOKEN}"
}

def req(function, status, url):
    r = function(url, headers = headers)
    if r.status_code != status:
        logging.error(f"Received unexpected status code {r.status_code} (expected {status})\n{r.reason}\n{r.text}")
        return False
    return r

def get_roles(guild_id):
    r = req(requests.get, 200, f"https://discord.com/api/v8/guilds/{guild_id}/roles")
    if r:
        try:
            logging.fatal(r.json())
            return r.json()
        except:
            return []

def verify_role(role_id, guild_id):
    roles = get_roles(guild_id)
    return True
