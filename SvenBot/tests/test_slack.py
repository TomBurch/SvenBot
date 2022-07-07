import json

from fastapi.testclient import TestClient
from pytest_httpx import HTTPXMock
from starlette.status import HTTP_200_OK

from SvenBot.config import settings
from SvenBot.main import app
from SvenBot.models import SlackNotification, SlackNotificationType, SlackEvent, SlackCalendarEvent, ResponseData, \
    Embed, EmbedField
from SvenBot.utility import CHANNELS_URL

client = TestClient(app)

startTime = 1657144680
endTime = 1657148280


def mockCalendarNotification(title):
    return SlackNotification(
        token="abca",
        type=SlackNotificationType.CALLBACK,
        event=SlackEvent(
            type="abc",
            text="abcdef",
            attachments=[SlackCalendarEvent(
                color="#colorrr",
                title=title,
                text=f"<!date^{startTime}^{{date_short_pretty}} from {{time}}|July 6th, 2022 from 9:58 PM> to <!date^{endTime}^{{time}}|10:58 PM Z>"
            )]
        )
    )


def test_random_event(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url=f"{CHANNELS_URL}/{settings.OP_CHANNEL}/messages",
        status_code=HTTP_200_OK
    )

    title = "ARCOMM random kind of event"
    notification = mockCalendarNotification(title)
    response = client.post("/slack/", json=notification.dict())

    assert response.status_code == HTTP_200_OK
    assert httpx_mock.get_request().content.decode() == ResponseData(
        content=None,
        allowed_mentions = {"parse": ["roles"]},
        embeds = [Embed(
            title=title,
            description = f"Starting <t:{startTime}:R>",
            fields=[
                EmbedField(name="Start", value=f"<t:{startTime}:t>", inline=True),
                EmbedField(name="End", value=f"<t:{endTime}:t>", inline=True)
            ]
        )]
    ).json()


def test_main_event(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url=f"{CHANNELS_URL}/{settings.OP_CHANNEL}/messages",
        status_code=HTTP_200_OK
    )

    title = "ARCOMM MAIN EVENT"
    notification = mockCalendarNotification(title)
    response = client.post("/slack/", json=notification.dict())

    assert response.status_code == HTTP_200_OK
    assert httpx_mock.get_request().content.decode() == ResponseData(
        content=f"<@&{settings.MEMBER_ROLE}>",
        allowed_mentions = {"parse": ["roles"]},
        embeds = [Embed(
            title=title,
            description = f"Starting <t:{startTime}:R>",
            fields=[
                EmbedField(name="Start", value=f"<t:{startTime}:t>", inline=True),
                EmbedField(name="End", value=f"<t:{endTime}:t>", inline=True)
            ]
        )]
    ).json()


def test_recruit_event(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url=f"{CHANNELS_URL}/{settings.OP_CHANNEL}/messages",
        status_code=HTTP_200_OK
    )

    title = "ARCOMM RECRUIT EVENT"
    notification = mockCalendarNotification(title)
    response = client.post("/slack/", json=notification.dict())

    assert response.status_code == HTTP_200_OK
    assert httpx_mock.get_request().content.decode() == ResponseData(
        content=f"<@&{settings.RECRUIT_ROLE}>",
        allowed_mentions = {"parse": ["roles"]},
        embeds = [Embed(
            title=title,
            description = f"Starting <t:{startTime}:R>",
            fields=[
                EmbedField(name="Start", value=f"<t:{startTime}:t>", inline=True),
                EmbedField(name="End", value=f"<t:{endTime}:t>", inline=True)
            ]
        )]
    ).json()
