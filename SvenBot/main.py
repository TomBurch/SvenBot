import json
import logging
import os
import re
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

from SvenBot.config import settings, EVENT_PINGS
from SvenBot.utility import sendMessage
from SvenBot.interactions import handle_interaction
from SvenBot.tasks import recruit_task, a3sync_task, steam_task
from SvenBot.models import InteractionType, Response, Interaction, InteractionResponseType, SlackNotification, \
    SlackNotificationType, Embed, EmbedField

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

    @fast_app.get('/abc/')
    def hello_world():
        return {"message", "Hello, World!"}

    @fast_app.post('/interaction/', response_model=Response)
    async def interact(interaction: Interaction = Body(...), valid: bool = Depends(ValidDiscordRequest())):
        if interaction.type == InteractionType.PING:
            return Response(type=InteractionResponseType.PONG)

        response = await handle_interaction(interaction)
        return response

    @fast_app.post('/slack/')
    async def interact(notification: SlackNotification = Body(...)):
        gunicorn_logger.error(f"Calendar event:\n{notification}")
        if notification.type == SlackNotificationType.VERIFICATION:
            return {'challenge': notification.challenge}

        cal = notification.event.attachments[0]
        times = re.match(r"<!date\^(\d+)\^\{\w+\} from.*to <!date\^(\d+)\^\{\w+}", cal.text)

        if times:
            event, ping, channel = None, None, settings.OP_CHANNEL
            for e, pc in EVENT_PINGS.items():
                if re.search(e, cal.text.lower()):
                    event, ping, channel = e, f"<@&{pc[0]}>", pc[1]
                    break

            startTime, endTime = times.groups()
            startField = EmbedField(name="Start", value=f"<t:{startTime}:t>", inline=True)
            endField = EmbedField(name="End", value=f"<t:{endTime}:t>", inline=True)
            embed = Embed(title=cal.title, description=f"Starting <t:{startTime}:R>", fields=[startField, endField])

            await sendMessage(channel, ping, embeds=[embed])

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
