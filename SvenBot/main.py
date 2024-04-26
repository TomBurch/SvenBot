import json
import logging
import os
import re
import sys
from datetime import datetime

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.params import Depends
from nacl.signing import VerifyKey
from starlette.status import HTTP_401_UNAUTHORIZED

PACKAGE_PARENT = ".."
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

from SvenBot.config import EVENT_PINGS, HUB_URL, settings, BASE_ARCHUB_URL
from SvenBot.interactions import handle_interaction
from SvenBot.models import (
    Embed,
    EmbedField,
    Interaction,
    InteractionResponseType,
    InteractionType,
    Response,
    SlackNotification,
    SlackNotificationType, EmbedThumbnail,
)
from SvenBot.tasks import a3sync_task, recruit_task, steam_task
from SvenBot.utility import getOperationMissions, sendMessage, mission_colour_from_mode

gunicorn_logger = logging.getLogger("gunicorn.error")


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

    @fast_app.get("/abc/")
    def hello_world():
        return {"message", "Hello, World!"}

    @fast_app.post("/interaction/", response_model=Response)
    async def interact(interaction: Interaction = Body(...), valid: bool = Depends(ValidDiscordRequest())):
        if interaction.type == InteractionType.PING:
            return Response(type=InteractionResponseType.PONG)

        return await handle_interaction(interaction)

    @fast_app.post("/slack/")
    async def slack(notification: SlackNotification = Body(...)):
        gunicorn_logger.error(f"Calendar event:\n{notification}")
        if notification.type == SlackNotificationType.VERIFICATION:
            return {"challenge": notification.challenge}

        cal = notification.event.attachments[0]
        matches = re.match(r"<!date\^(\d+)\^\{\w+\}.*? - <!date\^(\d+)\^\{\w+}.*?<.*?\|(.*)>", cal.title)

        if matches:
            event, pings, channel, color = None, None, settings.OP_CHANNEL, None
            for e, pcc in EVENT_PINGS.items():
                if re.search(e, cal.title.lower()):
                    pings = " ".join(f"<@&{ping}>" for ping in pcc[0])
                    event, channel, color = e, pcc[1], pcc[2]
                    break

            start_time, end_time, title = matches.groups()
            fields = [
                EmbedField(name="Start", value=f"<t:{start_time}:t>", inline=True),
                EmbedField(name="End", value=f"<t:{end_time}:t>", inline=True),
            ]
            embeds = [
                Embed(title=title, description=f"Starting <t:{start_time}:R>", fields=fields, color=color)
            ]

            if event == "main":
                for mission in await getOperationMissions():
                    link = f"{HUB_URL}/missions/{mission['id']}"
                    maker_string = "Maintained" if mission["hasMaintainer"] else "Made"

                    thumbnail: EmbedThumbnail | None
                    if " " in mission['thumbnail']:
                        print("Skipping thumbnail!")
                        thumbnail = None
                    else:
                        thumbnail = EmbedThumbnail(url=f"{BASE_ARCHUB_URL}{mission['thumbnail']}")

                    embeds.append(
                        Embed(title=mission['display_name'], description=f"{maker_string} by {mission['user']}",
                              url=link, thumbnail=thumbnail, color=mission_colour_from_mode(mission["mode"]))
                    )

            await sendMessage(channel, pings, ["roles"], embeds)

    return fast_app


app = app()


@app.on_event("startup")
def init_scheduler():
    try:
        with open("revision.json") as f:
            json.load(f)
    except Exception:
        with open("revision.json", "w") as f:
            json.dump({"revision": 0}, f)

    try:
        with open("steam_timestamp.json") as f:
            json.load(f)
    except Exception:
        with open("steam_timestamp.json", "w") as f:
            lastMonth = datetime.utcnow().timestamp() - 2500000
            json.dump({"last_checked": lastMonth}, f)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(recruit_task, "cron", day_of_week="mon,wed,fri", hour="17")
    scheduler.add_job(a3sync_task, "cron", minute="5,25,45")
    scheduler.add_job(steam_task, "cron", minute="20,50")
    scheduler.start()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
