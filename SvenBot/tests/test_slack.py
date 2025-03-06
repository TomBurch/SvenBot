from fastapi.testclient import TestClient
from pydantic import BaseModel
from pytest_httpx import HTTPXMock
from starlette.status import HTTP_200_OK

from SvenBot.config import (
    ARCHUB_API,
    ARCHUB_HEADERS,
    BASE_ARCHUB_URL,
    CHANNELS_URL,
    EVENT_PINGS,
    HUB_URL,
    settings,
)
from SvenBot.main import app
from SvenBot.models import (
    Embed,
    EmbedField,
    EmbedThumbnail,
    ResponseData,
    SlackCalendarEvent,
    SlackEvent,
    SlackNotification,
    SlackNotificationType,
)

client = TestClient(app)

startTime = 1657144680
endTime = 1657148280


class ArchubMission(BaseModel):
    id: int
    display_name: str
    mode: str
    user: str
    hasMaintainer: bool
    thumbnail: str = "/thumb"


def mock_calendar_notification(title: str) -> SlackNotification:
    return SlackNotification(
        token="abca",
        type=SlackNotificationType.CALLBACK,
        event=SlackEvent(
            type="abc",
            text="abcdef",
            attachments=[
                SlackCalendarEvent(
                    color="#colorrr",
                    text="random text",
                    title=f"<!date^{startTime}^{{time}}|7:00 PM> - <!date^{endTime}^{{time}}|11:00 PM> <https://www.google.com/calendar/event?eid=abc&amp;ctz=UTC|{title}>",
                )
            ],
        ),
    )


def test_random_event(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url=f"{CHANNELS_URL}/{settings.OP_CHANNEL}/messages",
        status_code=HTTP_200_OK,
    )

    title = "ARCOMM random kind of event"
    notification = mock_calendar_notification(title)
    response = client.post("/slack/", json=notification.dict())

    assert response.status_code == HTTP_200_OK
    assert (
        httpx_mock.get_request().content.decode()
        == ResponseData(
            content=None,
            allowed_mentions={"parse": ["roles"]},
            embeds=[
                Embed(
                    title=title,
                    description=f"Starting <t:{startTime}:R>",
                    fields=[
                        EmbedField(name="Start", value=f"<t:{startTime}:t>", inline=True),
                        EmbedField(name="End", value=f"<t:{endTime}:t>", inline=True),
                    ],
                )
            ],
        ).json()
    )


def test_main_event(httpx_mock: HTTPXMock):
    mission1 = ArchubMission(id=15, display_name="Random COOP", mode="coop", user="MissionMaker1", hasMaintainer=False)
    mission2 = ArchubMission(id=16, display_name="Random TVT", mode="tvt", user="MissionMaker2", hasMaintainer=False)
    mission3 = ArchubMission(id=17, display_name="Random ARCade", mode="ade", user="MissionMaker3", hasMaintainer=True)

    httpx_mock.add_response(
        method="GET",
        url=f"{ARCHUB_API}/operations/next",
        status_code=HTTP_200_OK,
        match_headers=ARCHUB_HEADERS,
        json=[mission1.dict(), mission2.dict(), mission3.dict()],
    )

    httpx_mock.add_response(
        method="POST",
        url=f"{CHANNELS_URL}/{settings.OP_CHANNEL}/messages",
        status_code=HTTP_200_OK,
    )

    title = "ARCOMM MAIN EVENT"
    notification = mock_calendar_notification(title)
    response = client.post("/slack/", json=notification.dict())

    assert response.status_code == HTTP_200_OK
    assert (
        httpx_mock.get_request(method="POST").content.decode()
        == ResponseData(
            content=f"<@&{settings.MEMBER_ROLE}> <@&{settings.RECRUIT_ROLE}>",
            allowed_mentions={"parse": ["roles"]},
            embeds=[
                Embed(
                    title=title,
                    description=f"Starting <t:{startTime}:R>",
                    fields=[
                        EmbedField(name="Start", value=f"<t:{startTime}:t>", inline=True),
                        EmbedField(name="End", value=f"<t:{endTime}:t>", inline=True),
                    ],
                    color=EVENT_PINGS["main"][2],
                ),
                Embed(
                    title=mission1.display_name,
                    url=f"{HUB_URL}/missions/{mission1.id}",
                    description=f"Made by {mission1.user}",
                    color=959977,
                    thumbnail=EmbedThumbnail(url=f"{BASE_ARCHUB_URL}{mission1.thumbnail}"),
                ),
                Embed(
                    title=mission2.display_name,
                    url=f"{HUB_URL}/missions/{mission2.id}",
                    description=f"Made by {mission2.user}",
                    color=16007006,
                    thumbnail=EmbedThumbnail(url=f"{BASE_ARCHUB_URL}{mission2.thumbnail}"),
                ),
                Embed(
                    title=mission3.display_name,
                    url=f"{HUB_URL}/missions/{mission3.id}",
                    description=f"Maintained by {mission3.user}",
                    color=1096065,
                    thumbnail=EmbedThumbnail(url=f"{BASE_ARCHUB_URL}{mission3.thumbnail}"),
                ),
            ],
        ).json()
    )


def test_recruit_event(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url=f"{CHANNELS_URL}/{settings.OP_CHANNEL}/messages",
        status_code=HTTP_200_OK,
    )

    title = "ARCOMM RECRUIT EVENT"
    notification = mock_calendar_notification(title)
    response = client.post("/slack/", json=notification.dict())

    assert response.status_code == HTTP_200_OK
    assert (
        httpx_mock.get_request().content.decode()
        == ResponseData(
            content=f"<@&{settings.RECRUIT_ROLE}>",
            allowed_mentions={"parse": ["roles"]},
            embeds=[
                Embed(
                    title=title,
                    description=f"Starting <t:{startTime}:R>",
                    fields=[
                        EmbedField(name="Start", value=f"<t:{startTime}:t>", inline=True),
                        EmbedField(name="End", value=f"<t:{endTime}:t>", inline=True),
                    ],
                    color=EVENT_PINGS["recruit"][2],
                )
            ],
        ).json()
    )
