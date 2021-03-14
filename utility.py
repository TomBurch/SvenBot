import logging
import os
import requests

from dotenv import load_dotenv

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
