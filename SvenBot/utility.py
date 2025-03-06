import logging
import re
from collections.abc import Callable, Coroutine
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from starlette.status import HTTP_200_OK, HTTP_204_NO_CONTENT

from SvenBot.config import (
    ARCHUB_API,
    ARCHUB_HEADERS,
    CHANNELS_URL,
    DEFAULT_HEADERS,
    GUILD_URL,
    settings,
)
from SvenBot.models import Embed, InteractionResponse, InteractionResponseType, ResponseData

gunicorn_logger = logging.getLogger("gunicorn.error")

client = httpx.AsyncClient()


async def req(
    function: Callable[..., Coroutine[Any, Any, httpx.Response]],
    statuses: list[int],
    url: str,
    headers: dict[str, str] = DEFAULT_HEADERS,
    **kwargs: Any,
) -> httpx.Response:
    response = await function(url, headers=headers, **kwargs)

    if response.status_code not in statuses:
        gunicorn_logger.error(
            f"Received unexpected status code {response.status_code} (expected {statuses})\n{response.text}",
        )
        raise RuntimeError(f"Req error: {response.text}")
    return response


async def get(statuses: list[int], url: str, **kwargs: Any) -> httpx.Response:
    return await req(client.get, statuses, url, **kwargs)


async def delete(statuses: list[int], url: str, **kwargs: Any) -> httpx.Response:
    return await req(client.delete, statuses, url, **kwargs)


async def put(statuses: list[int], url: str, **kwargs: Any) -> httpx.Response:
    return await req(client.put, statuses, url, **kwargs)


async def post(statuses: list[int], url: str, **kwargs: Any) -> httpx.Response:
    return await req(client.post, statuses, url, **kwargs)


async def patch(statuses: list[int], url: str, **kwargs: Any) -> httpx.Response:
    return await req(client.patch, statuses, url, **kwargs)


async def sendMessage(
    channel_id: int,
    text: str | None = None,
    mentions: list[str] = [],
    embeds: list[Embed] | None = None,
) -> ResponseData:
    message = ResponseData(content=text, embeds=embeds, allowed_mentions={"parse": mentions})
    await post([HTTP_200_OK], f"{CHANNELS_URL}/{channel_id}/messages", json=message.dict())

    return message


def ImmediateReply(content: str, mentions: list[str] = [], ephemeral: bool = False) -> InteractionResponse:
    data = ResponseData(content=content, allowed_mentions={"parse": mentions})
    if ephemeral:
        data.flags = 64

    return InteractionResponse(type=InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE, data=data)


def basicValidation(role: dict, botPosition: int) -> bool:
    return role.get("tags", {}).get("bot_id") is None and role["position"] < botPosition


def colourValidation(role: dict, botPosition: int) -> bool:
    return basicValidation(role, botPosition) and role["color"] == 0


role_validate_funcs: dict[str, Callable[[dict, int], bool]] = {
    "342006395010547712": colourValidation,
    "240160552867987475": colourValidation,
    "333316787603243018": basicValidation,
}


async def validateRole(guild_id: str, role: dict, roles: list[dict] | None = None) -> bool:
    if roles is None:
        roles = await getRoles(guild_id)

    botPosition = -1
    for r in roles:
        if r.get("tags", {}).get("bot_id") is not None:
            if r["tags"]["bot_id"] == settings.CLIENT_ID:
                botPosition = r["position"]
                break

    if botPosition == -1:
        raise RuntimeError("Unable to find bot's role")

    role_validate = role_validate_funcs.get(guild_id)
    if role_validate is None:
        return False
    return role_validate(role, botPosition)


async def validateRoleById(guild_id: str, role_id: str) -> bool:
    roleMatchingRoleId = None
    roles = await getRoles(guild_id)
    for r in roles:
        if r["id"] == role_id:
            roleMatchingRoleId = r
            break

    if roleMatchingRoleId is None:
        raise RuntimeError("Unable to find role")

    return await validateRole(guild_id, roleMatchingRoleId, roles)


async def getRoles(guild_id: str) -> list[dict]:
    roles = await get([HTTP_200_OK], f"{GUILD_URL}/{guild_id}/roles")
    return roles.json()


async def findRoleByName(
    guild_id: str,
    query: str,
    autocomplete: bool = False,
    excludeReserved: bool = True,
) -> dict | None:
    query = query.lower()
    roles = await getRoles(guild_id)
    candidate = None

    for role in roles:
        roleName = role["name"].lower()
        if roleName == query:
            candidate = role
            break

        if autocomplete and re.match(re.escape(query), roleName):
            candidate = role

    if excludeReserved and (candidate is not None):
        if await validateRole(guild_id, candidate, roles):
            return candidate
        return None

    return candidate


def timeUntilOptime(modifier: int = 0) -> timedelta:
    today = datetime.now(tz=ZoneInfo("Europe/London"))
    opday = today
    opday = opday.replace(hour=19, minute=0, second=0) + timedelta(hours=modifier)
    if today > opday:
        opday = opday + timedelta(days=1)

    return opday - today


async def getOperationMissions() -> list[dict]:
    response = await get([HTTP_200_OK, HTTP_204_NO_CONTENT], f"{ARCHUB_API}/operations/next", headers=ARCHUB_HEADERS)
    if response.status_code == HTTP_200_OK:
        return response.json()
    return []


def mission_colour_from_mode(mode: str) -> int:
    match mode:
        case "coop":
            return 959977
        case "tvt":
            return 16007006
        case "ade":
            return 1096065
