import logging
import os
import requests

from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

headers = {
    "Authorization": f"Bot {BOT_TOKEN}"
}

def req(function, statuses, url):
    r = function(url, headers = headers)
    if r.status_code not in statuses:
        logging.error(f"Received unexpected status code {r.status_code} (expected {status})\n{r.reason}\n{r.text}")
        return False
    return r
