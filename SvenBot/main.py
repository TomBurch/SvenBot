import json
import logging
import os
import sys
from datetime import datetime

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Body, Request, HTTPException
from fastapi.params import Depends
from nacl.signing import VerifyKey
from starlette.status import HTTP_401_UNAUTHORIZED

PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

from SvenBot.config import settings
from SvenBot.interactions import handle_interaction
from SvenBot.tasks import recruit_task, a3sync_task, steam_task
from SvenBot.models import InteractionType, Response, Interaction, InteractionResponseType, SlackEvent, SlackEventType

gunicorn_logger = logging.getLogger('gunicorn.error')


class ValidDiscordRequest:
    async def __call__(self, request: Request):
        signature = request.headers.get("X-Signature-Ed25519")
        timestamp = request.headers.get("X-Signature-Timestamp")
        body = await request.body()

        if signature is None or timestamp is None or not verify_key(body, signature, timestamp):
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Bad request signature")

        return True


def verify_key(body, signature, timestamp):
    message = timestamp.encode() + body

    try:
        VerifyKey(bytes.fromhex(settings.PUBLIC_KEY)).verify(message, bytes.fromhex(signature))
        return True
    except Exception as e:
        gunicorn_logger.error(e)
        return False


def app():
    fast_app = FastAPI()

    @fast_app.post('/interaction/', response_model=Response)
    async def interact(interaction: Interaction = Body(...), valid: bool = Depends(ValidDiscordRequest())):
        if interaction.type == InteractionType.PING:
            return Response(type=InteractionResponseType.PONG)

        response = await handle_interaction(interaction)
        return response

    @fast_app.post('/slack/')
    async def interact(event = Body(...)):
        gunicorn_logger.error(f"{event}")
        if event["type"] == SlackEventType.VERIFICATION:
            return {'challenge': event["challenge"]}

    @fast_app.get('/abc/')
    def hello_world():
        return {"message", "Hello, World!"}

    return fast_app


app = app()


@app.on_event('startup')
def init_scheduler():
    try:
        with open('revision.json', 'r') as f:
            json.load(f)
    except Exception as e:
        with open('revision.json', 'w') as f:
            json.dump({'revision': 0}, f)

    try:
        with open('steam_timestamp.json', 'r') as f:
            json.load(f)
    except Exception as e:
        with open('steam_timestamp.json', 'w') as f:
            lastMonth = datetime.utcnow().timestamp() - 2500000
            json.dump({'last_checked': lastMonth}, f)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(recruit_task, 'cron', day_of_week='mon,wed,fri', hour='17')
    scheduler.add_job(a3sync_task, 'cron', minute='5,25,45')
    scheduler.add_job(steam_task, 'cron', minute='20,50')
    scheduler.start()


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)
