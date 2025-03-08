import random
from datetime import datetime
from unittest import mock

import pytest
from d20 import RollSyntaxError
from fastapi import HTTPException
from freezegun import freeze_time
from pytest_httpx import HTTPXMock
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from SvenBot.config import (
    ARCHUB_API,
    ARCHUB_HEADERS,
    GITHUB_HEADERS,
    GUILD_URL,
    HUB_URL,
    settings,
)
from SvenBot.main import handle_interaction
from SvenBot.models import Interaction, InteractionType, Member, Option, OptionType
from SvenBot.utility import immediate_reply


class Role(dict):
    def __init__(self, _id: str, name: str, position: int, color: int = 0, bot_id: str | None = None) -> None:
        if bot_id is not None:
            dict.__init__(self, id=_id, name=name, position=position, color=color, tags={"bot_id": bot_id})
        else:
            dict.__init__(self, id=_id, name=name, position=position, color=color)


class MockRequest(dict):
    def __init__(self, name: str, member: Member | None = None, options: list[Option] = []) -> None:
        dict.__init__(
            self,
            type=InteractionType.APPLICATION_COMMAND,
            member=member,
            data={"name": name, "options": options, "id": "MockCommandId"},
            guild_id="342006395010547712",
            version=1,
            token="MockToken",
            application_id="MockAppId",
            id="MockRequestId",
        )


bot_role = Role("SvenBotRoleId", "SvenBot", 3, bot_id=settings.CLIENT_ID)
invalid_role = Role("RoleId789", "invalid_role", 1, color=10)
normal_role = Role("RoleId456", "normal_role", 2)
role_not_in_guild = Role("RoleId123", "role_not_in_guild", 5)

roles = [bot_role, normal_role, invalid_role]
arcomm_guild = "342006395010547712"

member_no_role = Member(user={"id": "User234", "username": "TestUser2", "discriminator": "4042"}, roles=[])
member_with_role = Member(user={"id": "User123", "username": "TestUser", "discriminator": "3124"}, roles=[normal_role["id"]])


@pytest.mark.asyncio
async def test_ping() -> None:
    interaction = Interaction(**MockRequest("ping", member_no_role))
    reply = await handle_interaction(interaction)
    expected = immediate_reply("Pong!")

    assert reply == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("httpx_mock", "user", "role", "role_method", "role_status", "reply_type"),
    [
        (None, member_with_role, normal_role, "DELETE", 204, "left"),
        (None, member_no_role, normal_role, "PUT", 204, "joined"),
        (None, member_with_role, normal_role, "DELETE", 403, "restricted"),
        (None, member_no_role, normal_role, "PUT", 403, "restricted"),
        (None, member_with_role, invalid_role, None, None, "restricted"),
        (None, member_no_role, invalid_role, None, None, "restricted"),
    ],
    indirect=["httpx_mock"],
)
async def test_role(
    httpx_mock: HTTPXMock,
    user: Member,
    role: Role,
    role_method: str | None,
    role_status: int | None,
    reply_type: str,
) -> None:
    user_id = user.user.id
    role_id = role["id"]

    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcomm_guild}/roles",
        json=roles,
        status_code=HTTP_200_OK,
    )

    if role_method is not None:
        httpx_mock.add_response(
            method=role_method,
            url=f"{GUILD_URL}/{arcomm_guild}/members/{user_id}/roles/{role_id}",
            status_code=role_status,
        )

    interaction = Interaction(
        **MockRequest("role", user, options=[Option(value=role_id, name="role", type=OptionType.ROLE)]),
    )
    reply = await handle_interaction(interaction)

    if reply_type in ("left", "joined"):
        assert reply == immediate_reply(f"You've {reply_type} <@&{role_id}>", mentions=[])
    elif reply_type == "restricted":
        assert reply == immediate_reply(f"<@&{role_id}> is restricted", mentions=[])
    else:
        pytest.fail("Unknown reply type")


@pytest.mark.asyncio
async def test_roles(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcomm_guild}/roles",
        json=roles,
        status_code=HTTP_200_OK,
    )

    interaction = Interaction(**MockRequest("roles", member_with_role))
    reply = await handle_interaction(interaction)

    assert reply == immediate_reply("```\n{}\n```".format(normal_role["name"]), mentions=[])


@pytest.mark.asyncio
async def test_roles_no_bot_role(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcomm_guild}/roles",
        json=[normal_role, invalid_role],
        status_code=HTTP_200_OK,
    )

    with pytest.raises(HTTPException), pytest.raises(RuntimeError, match="Unable to find bot's role"):
        interaction = Interaction(**MockRequest("roles", member_no_role))
        await handle_interaction(interaction)


@pytest.mark.asyncio
async def test_members(httpx_mock: HTTPXMock) -> None:
    role_id = normal_role["id"]

    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcomm_guild}/members?limit=200",
        json=[member_with_role.dict()],
        status_code=HTTP_200_OK,
    )

    interaction = Interaction(
        **MockRequest("members", member_no_role, options=[Option(value=role_id, name="role", type=OptionType.ROLE)]),
    )
    reply = await handle_interaction(interaction)

    username = member_with_role.user.username
    assert reply == immediate_reply(f"```\n{username}\n```", mentions=[])


@pytest.mark.asyncio
async def test_myroles() -> None:
    interaction = Interaction(**MockRequest("myroles", member_with_role))
    reply = await handle_interaction(interaction)

    assert reply == immediate_reply("<@&{}>\n".format(normal_role["id"]), mentions=[], ephemeral=True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("now_mock", "modifier", "time_until_optime"),
    [
        (datetime(2021, 3, 19, 15, 30), "", "3:30:00"),
        (datetime(2021, 3, 19, 19, 30, 42), "", "23:29:18"),
        (datetime(2021, 3, 19, 18, 0, 0), "", "1:00:00"),
        (datetime(2021, 3, 19, 18, 0, 0), " +1", "2:00:00"),
        (datetime(2021, 3, 19, 18, 0, 0), " -1", "0:00:00"),
        (datetime(2021, 3, 19, 18, 0, 0), " +7", "8:00:00"),
        (datetime(2021, 3, 19, 18, 0, 0), " -7", "18:00:00"),
    ],
)
async def test_optime(now_mock: datetime, modifier: str, time_until_optime: str) -> None:
    with freeze_time(now_mock):
        options = None if modifier == "" else [Option(value=int(modifier), name="modifier", type=OptionType.INTEGER)]
        interaction = Interaction(**MockRequest("optime", member_no_role, options=options))
        reply = await handle_interaction(interaction)

    assert reply == immediate_reply(f"Optime{modifier} starts in {time_until_optime}!", mentions=[])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("httpx_mock", "role_name", "role_id", "sends_post", "reply_type"),
    [
        (None, "NewRole", "NewRoleId", True, "added"),
        (None, "normal_role", "RoleId456", False, "already exists"),
    ],
    indirect=["httpx_mock"],
)
async def test_addrole(httpx_mock: HTTPXMock, role_name: str, role_id: str, sends_post: bool, reply_type: str) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcomm_guild}/roles",
        json=roles,
        status_code=HTTP_200_OK,
    )

    if sends_post:
        httpx_mock.add_response(
            method="POST",
            url=f"{GUILD_URL}/{arcomm_guild}/roles",
            json=Role(role_id, role_name, 4),
            status_code=HTTP_200_OK,
        )

    interaction = Interaction(
        **MockRequest("addrole", member_no_role, options=[Option(value=role_name, name="name", type=OptionType.STRING)]),
    )
    reply = await handle_interaction(interaction)

    assert reply == immediate_reply(f"<@&{role_id}> {reply_type}", mentions=[])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("httpx_mock", "role", "sends_delete", "reply_type"),
    [
        (None, normal_role, True, "Role deleted"),
        (None, invalid_role, False, "Role is restricted"),
    ],
    indirect=["httpx_mock"],
)
async def test_removerole(httpx_mock: HTTPXMock, role: Role, sends_delete: bool, reply_type: str) -> None:
    role_id = role["id"]

    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcomm_guild}/roles",
        json=roles,
        status_code=HTTP_200_OK,
    )

    if sends_delete:
        httpx_mock.add_response(
            method="DELETE",
            url=f"{GUILD_URL}/{arcomm_guild}/roles/{role_id}",
            status_code=HTTP_204_NO_CONTENT,
        )

    interaction = Interaction(
        **MockRequest("removerole", member_no_role, options=[Option(value=role_id, name="role", type=OptionType.ROLE)]),
    )
    reply = await handle_interaction(interaction)

    assert reply == immediate_reply(reply_type, mentions=[])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("httpx_mock", "status_code", "reply_type"),
    [
        (None, HTTP_201_CREATED, "You are now subscribed to"),
        (None, HTTP_204_NO_CONTENT, "You are no longer subscribed to"),
    ],
    indirect=["httpx_mock"],
)
async def test_subscribe(httpx_mock: HTTPXMock, status_code: int, reply_type: str) -> None:
    mission_id = 900
    user_id = member_no_role.user.id

    httpx_mock.add_response(
        method="POST",
        url=f"{ARCHUB_API}/missions/{mission_id}/subscribe?discord_id={user_id}",
        status_code=status_code,
        match_headers=ARCHUB_HEADERS,
    )

    interaction = Interaction(
        **MockRequest(
            "subscribe",
            member_no_role,
            options=[Option(value=mission_id, name="subscribe", type=OptionType.INTEGER)],
        ),
    )
    reply = await handle_interaction(interaction)
    expected = f"{reply_type} {HUB_URL}/missions/{mission_id}"

    assert reply == immediate_reply(expected, mentions=[])


@pytest.mark.asyncio
async def test_ticket(httpx_mock: HTTPXMock) -> None:
    created_url = "https://github.com/ARCOMM/ArcommBot/issues/64"

    httpx_mock.add_response(
        method="POST",
        url="https://api.github.com/repos/TomBurch/SvenBot/issues",
        json={"html_url": created_url},
        status_code=HTTP_201_CREATED,
        match_headers=GITHUB_HEADERS,
    )

    options = [
        Option(value="TomBurch/SvenBot", name="repo", type=OptionType.STRING),
        Option(value="Test title", name="title", type=OptionType.STRING),
        Option(value="Test body", name="body", type=OptionType.STRING),
    ]
    interaction = Interaction(**MockRequest("ticket", member_no_role, options=options))
    reply = await handle_interaction(interaction)
    expected = f"Ticket created at: {created_url}"

    assert reply == immediate_reply(expected, mentions=[])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("httpx_mock", "coin"),
    [
        (None, "Heads"),
        (None, "Tails"),
    ],
    indirect=["httpx_mock"],
)
async def test_cointoss(httpx_mock: HTTPXMock, coin: str) -> None:
    interaction = Interaction(**MockRequest("cointoss", member_no_role))

    with mock.patch.object(random, "choice") as m:
        m.return_value = coin
        reply = await handle_interaction(interaction)
        assert reply == immediate_reply(coin)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("httpx_mock", "roll_str", "error_expected"),
    [
        (None, "1d6", False),
        (None, "aaa", True),
    ],
    indirect=["httpx_mock"],
)
async def test_d20(httpx_mock: HTTPXMock, roll_str: str, error_expected: bool) -> None:
    interaction = Interaction(
        **MockRequest("d20", member_no_role, options=[Option(value=roll_str, name="options", type=OptionType.STRING)]),
    )

    if error_expected:
        with pytest.raises(HTTPException), pytest.raises(RollSyntaxError):
            await handle_interaction(interaction)
    else:
        await handle_interaction(interaction)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("httpx_mock", "role", "new_name", "patches", "reply_type"),
    [
        (None, normal_role, "RandomName", True, "was renamed"),
        (None, invalid_role, "RandomName", False, "is restricted"),
        (None, normal_role, invalid_role["name"], False, "already exists"),
    ],
    indirect=["httpx_mock"],
)
async def test_renamerole(httpx_mock: HTTPXMock, role: Role, new_name: str, patches: bool, reply_type: str) -> None:
    role_id = role["id"]

    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcomm_guild}/roles",
        json=roles,
        status_code=HTTP_200_OK,
    )

    if patches:
        httpx_mock.add_response(
            method="PATCH",
            url=f"{GUILD_URL}/{arcomm_guild}/roles/{role_id}",
            status_code=HTTP_200_OK,
        )

    interaction = Interaction(
        **MockRequest(
            "renamerole",
            member_no_role,
            options=[
                Option(value=role_id, name="role", type=OptionType.ROLE),
                Option(value=new_name, name="name", type=OptionType.STRING),
            ],
        ),
    )
    reply = await handle_interaction(interaction)

    if new_name == invalid_role["name"]:
        role_id = invalid_role["id"]
        assert reply == immediate_reply(f"<@&{role_id}> {reply_type}", mentions=[])
    else:
        assert reply == immediate_reply(f"<@&{role_id}> {reply_type}", mentions=[])


@pytest.mark.asyncio
async def test_maps(httpx_mock: HTTPXMock) -> None:
    maps = [{"class_name": "map1class", "display_name": "map1display"}]
    httpx_mock.add_response(
        method="GET",
        url=f"{ARCHUB_API}/maps",
        json=maps,
        status_code=HTTP_200_OK,
        match_headers=ARCHUB_HEADERS,
    )

    interaction = Interaction(**MockRequest("maps", member_no_role, options=[]))
    reply = await handle_interaction(interaction)

    out_string = f"```ini\nFile name [Display name]\n=========================\n{maps[0]['class_name']} [{maps[0]['display_name']}]\n```"
    assert reply == immediate_reply(out_string, mentions=[])


@pytest.mark.asyncio
async def test_renamemap(httpx_mock: HTTPXMock) -> None:
    old_name, new_name = "abc", "def"
    httpx_mock.add_response(
        method="PATCH",
        url=f"{ARCHUB_API}/maps?old_name={old_name}&new_name={new_name}",
        status_code=HTTP_204_NO_CONTENT,
        match_headers=ARCHUB_HEADERS,
    )

    interaction = Interaction(
        **MockRequest(
            "renamemap",
            member_no_role,
            options=[
                Option(value=old_name, name="old_name", type=OptionType.STRING),
                Option(value=new_name, name="new_name", type=OptionType.STRING),
            ],
        ),
    )
    reply = await handle_interaction(interaction)

    assert reply == immediate_reply(f"`{old_name}` was renamed to `{new_name}`", mentions=[])


if __name__ == "__main__":
    pytest.main()
