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
from SvenBot.utility import ImmediateReply


class Role(dict):
    def __init__(self, _id: str, name: str, position: int, color: int = 0, botId: str | None = None) -> None:
        if botId is not None:
            dict.__init__(self, id=_id, name=name, position=position, color=color, tags={"bot_id": botId})
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


botRole = Role("SvenBotRoleId", "SvenBot", 3, botId=settings.CLIENT_ID)
invalidRole = Role("RoleId789", "InvalidRole", 1, color=10)
testRole = Role("RoleId456", "TestRole", 2)
roleNotInGuild = Role("RoleId123", "RoleNotInGuild", 5)

roles = [botRole, testRole, invalidRole]
arcommGuild = "342006395010547712"

memberNoRole = Member(user={"id": "User234", "username": "TestUser2", "discriminator": "4042"}, roles=[])
memberWithRole = Member(user={"id": "User123", "username": "TestUser", "discriminator": "3124"}, roles=[testRole["id"]])


@pytest.mark.asyncio
async def test_ping() -> None:
    interaction = Interaction(**MockRequest("ping", memberNoRole))
    reply = await handle_interaction(interaction)
    expected = ImmediateReply("Pong!")

    assert reply == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("httpx_mock", "user", "role", "roleMethod", "roleStatus", "replyType"),
    [
        (None, memberWithRole, testRole, "DELETE", 204, "left"),
        (None, memberNoRole, testRole, "PUT", 204, "joined"),
        (None, memberWithRole, testRole, "DELETE", 403, "restricted"),
        (None, memberNoRole, testRole, "PUT", 403, "restricted"),
        (None, memberWithRole, invalidRole, None, None, "restricted"),
        (None, memberNoRole, invalidRole, None, None, "restricted"),
    ],
    indirect=["httpx_mock"],
)
async def test_role(
    httpx_mock: HTTPXMock,
    user: Member,
    role: Role,
    roleMethod: str | None,
    roleStatus: int | None,
    replyType: str,
) -> None:
    userId = user.user.id
    roleId = role["id"]

    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcommGuild}/roles",
        json=roles,
        status_code=HTTP_200_OK,
    )

    if roleMethod is not None:
        httpx_mock.add_response(
            method=roleMethod,
            url=f"{GUILD_URL}/{arcommGuild}/members/{userId}/roles/{roleId}",
            status_code=roleStatus,
        )

    interaction = Interaction(
        **MockRequest("role", user, options=[Option(value=roleId, name="role", type=OptionType.ROLE)]),
    )
    reply = await handle_interaction(interaction)

    if replyType in ("left", "joined"):
        assert reply == ImmediateReply(f"You've {replyType} <@&{roleId}>", mentions=[])
    elif replyType == "restricted":
        assert reply == ImmediateReply(f"<@&{roleId}> is restricted", mentions=[])
    else:
        pytest.fail("Unknown reply type")


@pytest.mark.asyncio
async def test_roles(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcommGuild}/roles",
        json=roles,
        status_code=HTTP_200_OK,
    )

    interaction = Interaction(**MockRequest("roles", memberWithRole))
    reply = await handle_interaction(interaction)

    assert reply == ImmediateReply("```\n{}\n```".format(testRole["name"]), mentions=[])


@pytest.mark.asyncio
async def test_rolesNoBotRole(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcommGuild}/roles",
        json=[testRole, invalidRole],
        status_code=HTTP_200_OK,
    )

    with pytest.raises(HTTPException), pytest.raises(RuntimeError, match="Unable to find bot's role"):
        interaction = Interaction(**MockRequest("roles", memberNoRole))
        await handle_interaction(interaction)


@pytest.mark.asyncio
async def test_members(httpx_mock: HTTPXMock) -> None:
    roleId = testRole["id"]

    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcommGuild}/members?limit=200",
        json=[memberWithRole.dict()],
        status_code=HTTP_200_OK,
    )

    interaction = Interaction(
        **MockRequest("members", memberNoRole, options=[Option(value=roleId, name="role", type=OptionType.ROLE)]),
    )
    reply = await handle_interaction(interaction)

    username = memberWithRole.user.username
    assert reply == ImmediateReply(f"```\n{username}\n```", mentions=[])


@pytest.mark.asyncio
async def test_myroles() -> None:
    interaction = Interaction(**MockRequest("myroles", memberWithRole))
    reply = await handle_interaction(interaction)

    assert reply == ImmediateReply("<@&{}>\n".format(testRole["id"]), mentions=[], ephemeral=True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("now_mock", "modifier", "timeUntilOptime"),
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
async def test_optime(now_mock: datetime, modifier: str, timeUntilOptime: str) -> None:
    with freeze_time(now_mock):
        options = None if modifier == "" else [Option(value=int(modifier), name="modifier", type=OptionType.INTEGER)]
        interaction = Interaction(**MockRequest("optime", memberNoRole, options=options))
        reply = await handle_interaction(interaction)

    assert reply == ImmediateReply(f"Optime{modifier} starts in {timeUntilOptime}!", mentions=[])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("httpx_mock", "roleName", "roleId", "sendsPost", "replyType"),
    [
        (None, "NewRole", "NewRoleId", True, "added"),
        (None, "TestRole", "RoleId456", False, "already exists"),
    ],
    indirect=["httpx_mock"],
)
async def test_addrole(httpx_mock: HTTPXMock, roleName: str, roleId: str, sendsPost: bool, replyType: str) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcommGuild}/roles",
        json=roles,
        status_code=HTTP_200_OK,
    )

    if sendsPost:
        httpx_mock.add_response(
            method="POST",
            url=f"{GUILD_URL}/{arcommGuild}/roles",
            json=Role(roleId, roleName, 4),
            status_code=HTTP_200_OK,
        )

    interaction = Interaction(
        **MockRequest("addrole", memberNoRole, options=[Option(value=roleName, name="name", type=OptionType.STRING)]),
    )
    reply = await handle_interaction(interaction)

    assert reply == ImmediateReply(f"<@&{roleId}> {replyType}", mentions=[])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("httpx_mock", "role", "sendsDelete", "replyType"),
    [
        (None, testRole, True, "Role deleted"),
        (None, invalidRole, False, "Role is restricted"),
    ],
    indirect=["httpx_mock"],
)
async def test_removerole(httpx_mock: HTTPXMock, role: Role, sendsDelete: bool, replyType: str) -> None:
    roleId = role["id"]

    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcommGuild}/roles",
        json=roles,
        status_code=HTTP_200_OK,
    )

    if sendsDelete:
        httpx_mock.add_response(
            method="DELETE",
            url=f"{GUILD_URL}/{arcommGuild}/roles/{roleId}",
            status_code=HTTP_204_NO_CONTENT,
        )

    interaction = Interaction(
        **MockRequest("removerole", memberNoRole, options=[Option(value=roleId, name="role", type=OptionType.ROLE)]),
    )
    reply = await handle_interaction(interaction)

    assert reply == ImmediateReply(replyType, mentions=[])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("httpx_mock", "statusCode", "replyType"),
    [
        (None, HTTP_201_CREATED, "You are now subscribed to"),
        (None, HTTP_204_NO_CONTENT, "You are no longer subscribed to"),
    ],
    indirect=["httpx_mock"],
)
async def test_subscribe(httpx_mock: HTTPXMock, statusCode: int, replyType: str) -> None:
    missionId = 900
    userId = memberNoRole.user.id

    httpx_mock.add_response(
        method="POST",
        url=f"{ARCHUB_API}/missions/{missionId}/subscribe?discord_id={userId}",
        status_code=statusCode,
        match_headers=ARCHUB_HEADERS,
    )

    interaction = Interaction(
        **MockRequest(
            "subscribe",
            memberNoRole,
            options=[Option(value=missionId, name="subscribe", type=OptionType.INTEGER)],
        ),
    )
    reply = await handle_interaction(interaction)
    expected = f"{replyType} {HUB_URL}/missions/{missionId}"

    assert reply == ImmediateReply(expected, mentions=[])


@pytest.mark.asyncio
async def test_ticket(httpx_mock: HTTPXMock) -> None:
    createdUrl = "https://github.com/ARCOMM/ArcommBot/issues/64"

    httpx_mock.add_response(
        method="POST",
        url="https://api.github.com/repos/TomBurch/SvenBot/issues",
        json={"html_url": createdUrl},
        status_code=HTTP_201_CREATED,
        match_headers=GITHUB_HEADERS,
    )

    options = [
        Option(value="TomBurch/SvenBot", name="repo", type=OptionType.STRING),
        Option(value="Test title", name="title", type=OptionType.STRING),
        Option(value="Test body", name="body", type=OptionType.STRING),
    ]
    interaction = Interaction(**MockRequest("ticket", memberNoRole, options=options))
    reply = await handle_interaction(interaction)
    expected = f"Ticket created at: {createdUrl}"

    assert reply == ImmediateReply(expected, mentions=[])


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
    interaction = Interaction(**MockRequest("cointoss", memberNoRole))

    with mock.patch.object(random, "choice") as m:
        m.return_value = coin
        reply = await handle_interaction(interaction)
        assert reply == ImmediateReply(coin)


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
        **MockRequest("d20", memberNoRole, options=[Option(value=roll_str, name="options", type=OptionType.STRING)]),
    )

    if error_expected:
        with pytest.raises(HTTPException), pytest.raises(RollSyntaxError):
            await handle_interaction(interaction)
    else:
        await handle_interaction(interaction)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("httpx_mock", "role", "newName", "patches", "replyType"),
    [
        (None, testRole, "RandomName", True, "was renamed"),
        (None, invalidRole, "RandomName", False, "is restricted"),
        (None, testRole, invalidRole["name"], False, "already exists"),
    ],
    indirect=["httpx_mock"],
)
async def test_renamerole(httpx_mock: HTTPXMock, role: Role, newName: str, patches: bool, replyType: str) -> None:
    roleId = role["id"]

    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcommGuild}/roles",
        json=roles,
        status_code=HTTP_200_OK,
    )

    if patches:
        httpx_mock.add_response(
            method="PATCH",
            url=f"{GUILD_URL}/{arcommGuild}/roles/{roleId}",
            status_code=HTTP_200_OK,
        )

    interaction = Interaction(
        **MockRequest(
            "renamerole",
            memberNoRole,
            options=[
                Option(value=roleId, name="role", type=OptionType.ROLE),
                Option(value=newName, name="name", type=OptionType.STRING),
            ],
        ),
    )
    reply = await handle_interaction(interaction)

    if newName == invalidRole["name"]:
        roleId = invalidRole["id"]
        assert reply == ImmediateReply(f"<@&{roleId}> {replyType}", mentions=[])
    else:
        assert reply == ImmediateReply(f"<@&{roleId}> {replyType}", mentions=[])


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

    interaction = Interaction(**MockRequest("maps", memberNoRole, options=[]))
    reply = await handle_interaction(interaction)

    outString = f"```ini\nFile name [Display name]\n=========================\n{maps[0]['class_name']} [{maps[0]['display_name']}]\n```"
    assert reply == ImmediateReply(outString, mentions=[])


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
            memberNoRole,
            options=[
                Option(value=old_name, name="old_name", type=OptionType.STRING),
                Option(value=new_name, name="new_name", type=OptionType.STRING),
            ],
        ),
    )
    reply = await handle_interaction(interaction)

    assert reply == ImmediateReply(f"`{old_name}` was renamed to `{new_name}`", mentions=[])


if __name__ == "__main__":
    pytest.main()
