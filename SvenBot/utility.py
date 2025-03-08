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


async def send_message(
    channel_id: int,
    text: str | None = None,
    mentions: list[str] = [],
    embeds: list[Embed] | None = None,
) -> ResponseData:
    message = ResponseData(content=text, embeds=embeds, allowed_mentions={"parse": mentions})
    await post([HTTP_200_OK], f"{CHANNELS_URL}/{channel_id}/messages", json=message.dict())

    return message


def immediate_reply(content: str, mentions: list[str] = [], ephemeral: bool = False) -> InteractionResponse:
    data = ResponseData(content=content, allowed_mentions={"parse": mentions})
    if ephemeral:
        data.flags = 64

    return InteractionResponse(type=InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE, data=data)


def basic_validation(role: dict, bot_position: int) -> bool:
    return role.get("tags", {}).get("bot_id") is None and role["position"] < bot_position


def colour_validation(role: dict, bot_position: int) -> bool:
    return basic_validation(role, bot_position) and role["color"] == 0


role_validate_funcs: dict[str, Callable[[dict, int], bool]] = {
    "342006395010547712": colour_validation,
    "240160552867987475": colour_validation,
    "333316787603243018": basic_validation,
}


async def validate_role(guild_id: str, role: dict, roles: list[dict] | None = None) -> bool:
    if roles is None:
        roles = await get_roles(guild_id)

    bot_position = -1
    for r in roles:
        if r.get("tags", {}).get("bot_id") is not None:
            if r["tags"]["bot_id"] == settings.CLIENT_ID:
                bot_position = r["position"]
                break

    if bot_position == -1:
        raise RuntimeError("Unable to find bot's role")

    role_validate = role_validate_funcs.get(guild_id)
    if role_validate is None:
        return False
    return role_validate(role, bot_position)


async def validate_role_by_id(guild_id: str, role_id: str) -> bool:
    role_matching_role_id = None
    roles = await get_roles(guild_id)
    for r in roles:
        if r["id"] == role_id:
            role_matching_role_id = r
            break

    if role_matching_role_id is None:
        raise RuntimeError("Unable to find role")

    return await validate_role(guild_id, role_matching_role_id, roles)


async def get_roles(guild_id: str) -> list[dict]:
    roles = await get([HTTP_200_OK], f"{GUILD_URL}/{guild_id}/roles")
    return roles.json()


async def find_role_by_name(
    guild_id: str,
    query: str,
    autocomplete: bool = False,
    exclude_reserved: bool = True,
) -> dict | None:
    query = query.lower()
    roles = await get_roles(guild_id)
    candidate = None

    for role in roles:
        role_name = role["name"].lower()
        if role_name == query:
            candidate = role
            break

        if autocomplete and re.match(re.escape(query), role_name):
            candidate = role

    if exclude_reserved and (candidate is not None):
        if await validate_role(guild_id, candidate, roles):
            return candidate
        return None

    return candidate


def time_until_optime(modifier: int = 0) -> timedelta:
    today = datetime.now(tz=ZoneInfo("Europe/London"))
    opday = today
    opday = opday.replace(hour=19, minute=0, second=0) + timedelta(hours=modifier)
    if today > opday:
        opday = opday + timedelta(days=1)

    return opday - today


async def get_operation_missions() -> list[dict]:
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
