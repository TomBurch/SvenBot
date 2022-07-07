from fastapi.testclient import TestClient
from pydantic import BaseModel
from pytest_httpx import HTTPXMock
from starlette.status import HTTP_200_OK

from SvenBot.config import settings, EVENT_PINGS, CHANNELS_URL, ARCHUB_API, ARCHUB_HEADERS, HUB_URL
from SvenBot.main import app
from SvenBot.models import SlackNotification, SlackNotificationType, SlackEvent, SlackCalendarEvent, ResponseData, \
    Embed, EmbedField

client = TestClient(app)

startTime = 1657144680
endTime = 1657148280


class ArchubMission(BaseModel):
    id: int
    display_name: str
    mode: str
    maker: str


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
    mission1 = ArchubMission(id=15, display_name='Random COOP', mode='coop', maker='MissionMaker1')
    mission2 = ArchubMission(id=16, display_name='Random TVT', mode='adversarial', maker='MissionMaker2')
    mission3 = ArchubMission(id=17, display_name='Random ARCade', mode='arcade', maker='MissionMaker3')

    httpx_mock.add_response(
        method="GET",
        url=f"{ARCHUB_API}/operations/next",
        status_code=HTTP_200_OK,
        match_headers=ARCHUB_HEADERS,
        json=[mission1.dict(), mission2.dict(), mission3.dict()]
    )

    httpx_mock.add_response(
        method="POST",
        url=f"{CHANNELS_URL}/{settings.OP_CHANNEL}/messages",
        status_code=HTTP_200_OK
    )

    title = "ARCOMM MAIN EVENT"
    notification = mockCalendarNotification(title)
    response = client.post("/slack/", json=notification.dict())

    assert response.status_code == HTTP_200_OK
    assert httpx_mock.get_request(method="POST").content.decode() == ResponseData(
        content=f"<@&{settings.MEMBER_ROLE}>",
        allowed_mentions = {"parse": ["roles"]},
        embeds = [Embed(
            title=title,
            description = f"Starting <t:{startTime}:R>",
            fields=[
                EmbedField(name="Start", value=f"<t:{startTime}:t>", inline=True),
                EmbedField(name="End", value=f"<t:{endTime}:t>", inline=True),
                EmbedField(name=mission1.display_name, value=f"[Co-op by {mission1.maker}]({HUB_URL}/missions/{mission1.id})", inline=False),
                EmbedField(name=mission2.display_name, value=f"[TvT by {mission2.maker}]({HUB_URL}/missions/{mission2.id})", inline=False),
                EmbedField(name=mission3.display_name, value=f"[ARCade by {mission3.maker}]({HUB_URL}/missions/{mission3.id})", inline=False),
            ],
            color=EVENT_PINGS['main'][2]
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
            ],
            color=EVENT_PINGS['recruit'][2]
        )]
    ).json()
