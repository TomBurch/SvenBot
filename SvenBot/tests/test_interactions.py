import random
from datetime import datetime
from unittest import mock

import pytest
from fastapi import HTTPException
from freezegun import freeze_time
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_200_OK

from SvenBot.config import settings
from SvenBot.main import handle_interaction
from SvenBot.models import InteractionType, Member, Interaction, Option, OptionType
from SvenBot.utility import ImmediateReply, ARCHUB_HEADERS, GITHUB_HEADERS, GUILD_URL, ARCHUB_URL


class Role(dict):
    def __init__(self, _id, name, position, color=0, botId=None):
        if botId is not None:
            dict.__init__(self, id=_id, name=name, position=position, color=color, tags={"bot_id": botId})
        else:
            dict.__init__(self, id=_id, name=name, position=position, color=color)


class MockRequest(dict):
    def __init__(self, name, member=None, options=[]):
        dict.__init__(self, type=InteractionType.APPLICATION_COMMAND, member=member,
                      data={"name": name, "options": options, "id": "MockCommandId"},
                      guild_id="342006395010547712", version=1, token="MockToken", application_id="MockAppId",
                      id="MockRequestId")


botRole = Role("SvenBotRoleId", "SvenBot", 3, botId=settings.CLIENT_ID)
invalidRole = Role("RoleId789", "InvalidRole", 1, color=10)
testRole = Role("RoleId456", "TestRole", 2)
roleNotInGuild = Role("RoleId123", "RoleNotInGuild", 5)

roles = [botRole, testRole, invalidRole]
arcommGuild = "342006395010547712"

memberNoRole = Member(user={"id": "User234", "username": "TestUser2", "discriminator": "4042"}, roles=[])
memberWithRole = Member(user={"id": "User123", "username": "TestUser", "discriminator": "3124"}, roles=[testRole["id"]])


@pytest.mark.asyncio
async def test_ping():
    interaction = Interaction(**MockRequest("ping", memberNoRole))
    reply = await handle_interaction(interaction)
    expected = ImmediateReply("Pong!")

    assert reply == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("httpx_mock, user, role, roleMethod, roleStatus, replyType", [
    (None, memberWithRole, testRole, "DELETE", 204, "left"),
    (None, memberNoRole, testRole, "PUT", 204, "joined"),
    (None, memberWithRole, testRole, "DELETE", 403, "restricted"),
    (None, memberNoRole, testRole, "PUT", 403, "restricted"),
    (None, memberWithRole, invalidRole, None, None, "restricted"),
    (None, memberNoRole, invalidRole, None, None, "restricted")
], indirect=["httpx_mock"])
async def test_role(httpx_mock, user, role, roleMethod, roleStatus, replyType):
    userId = user.user.id
    roleId = role["id"]

    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcommGuild}/roles",
        json=roles,
        status_code=HTTP_200_OK
    )

    if roleMethod is not None:
        httpx_mock.add_response(
            method=roleMethod,
            url=f"{GUILD_URL}/{arcommGuild}/members/{userId}/roles/{roleId}",
            status_code=roleStatus
        )

    interaction = Interaction(
        **MockRequest("role", user, options=[Option(value=roleId, name="role", type=OptionType.ROLE)]))
    reply = await handle_interaction(interaction)

    if replyType == "left" or replyType == "joined":
        assert reply == ImmediateReply(f"You've {replyType} <@&{roleId}>", mentions=[])
    elif replyType == "restricted":
        assert reply == ImmediateReply(f"<@&{roleId}> is restricted", mentions=[])
    else:
        assert False


@pytest.mark.asyncio
async def test_roles(httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcommGuild}/roles",
        json=roles,
        status_code=HTTP_200_OK
    )

    interaction = Interaction(**MockRequest("roles", memberWithRole))
    reply = await handle_interaction(interaction)

    assert reply == ImmediateReply("```\n{}\n```".format(testRole["name"]), mentions=[])


@pytest.mark.asyncio
async def test_rolesNoBotRole(httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcommGuild}/roles",
        json=[testRole, invalidRole],
        status_code=HTTP_200_OK
    )

    with pytest.raises(HTTPException) as e2:
        with pytest.raises(RuntimeError, match="Unable to find bot's role") as e1:
            interaction = Interaction(**MockRequest("roles", memberNoRole))
            await handle_interaction(interaction)


@pytest.mark.asyncio
async def test_members(httpx_mock):
    roleId = testRole["id"]

    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcommGuild}/members?limit=200",
        json=[memberWithRole.dict()],
        status_code=HTTP_200_OK
    )

    interaction = Interaction(
        **MockRequest("members", memberNoRole, options=[Option(value=roleId, name="role", type=OptionType.ROLE)]))
    reply = await handle_interaction(interaction)

    username = memberWithRole.user.username
    assert reply == ImmediateReply(f"```\n{username}\n```", mentions=[])


@pytest.mark.asyncio
async def test_myroles():
    interaction = Interaction(**MockRequest("myroles", memberWithRole))
    reply = await handle_interaction(interaction)

    assert reply == ImmediateReply("<@&{}>\n".format(testRole["id"]), mentions=[], ephemeral=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("now_mock, modifier, timeUntilOptime", [
    (datetime(2021, 3, 19, 15, 30), "", "2:30:00"),
    (datetime(2021, 3, 19, 19, 30, 42), "", "22:29:18"),
    (datetime(2021, 3, 19, 18, 0, 0), "", "0:00:00"),
    (datetime(2021, 3, 19, 18, 0, 0), " +1", "1:00:00"),
    (datetime(2021, 3, 19, 18, 0, 0), " -1", "23:00:00"),
    (datetime(2021, 3, 19, 18, 0, 0), " +7", "7:00:00"),
    (datetime(2021, 3, 19, 18, 0, 0), " -7", "17:00:00")
])
async def test_optime(now_mock, modifier, timeUntilOptime):
    with freeze_time(now_mock):
        options = None if modifier == "" else [Option(value=int(modifier), name="modifier", type=OptionType.INTEGER)]
        interaction = Interaction(**MockRequest("optime", memberNoRole, options=options))
        reply = await handle_interaction(interaction)

    assert reply == ImmediateReply(f"Optime{modifier} starts in {timeUntilOptime}!", mentions=[])


@pytest.mark.asyncio
@pytest.mark.parametrize("httpx_mock, roleName, roleId, sendsPost, replyType", [
    (None, "NewRole", "NewRoleId", True, "added"),
    (None, "TestRole", "RoleId456", False, "already exists")
], indirect=["httpx_mock"])
async def test_addrole(httpx_mock, roleName, roleId, sendsPost, replyType):
    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcommGuild}/roles",
        json=roles,
        status_code=HTTP_200_OK
    )

    if sendsPost:
        httpx_mock.add_response(
            method="POST",
            url=f"{GUILD_URL}/{arcommGuild}/roles",
            json=Role(roleId, roleName, 4),
            status_code=HTTP_200_OK
        )

    interaction = Interaction(
        **MockRequest("addrole", memberNoRole, options=[Option(value=roleName, name="name", type=OptionType.STRING)]))
    reply = await handle_interaction(interaction)

    assert reply == ImmediateReply(f"<@&{roleId}> {replyType}", mentions=[])


@pytest.mark.asyncio
@pytest.mark.parametrize("httpx_mock, role, sendsDelete, replyType", [
    (None, testRole, True, "Role deleted"),
    (None, invalidRole, False, "Role is restricted")
], indirect=["httpx_mock"])
async def test_removerole(httpx_mock, role, sendsDelete, replyType):
    roleId = role["id"]

    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcommGuild}/roles",
        json=roles,
        status_code=HTTP_200_OK
    )

    if sendsDelete:
        httpx_mock.add_response(
            method="DELETE",
            url=f"{GUILD_URL}/{arcommGuild}/roles/{roleId}",
            status_code=HTTP_204_NO_CONTENT
        )

    interaction = Interaction(
        **MockRequest("removerole", memberNoRole, options=[Option(value=roleId, name="role", type=OptionType.ROLE)]))
    reply = await handle_interaction(interaction)

    assert reply == ImmediateReply(replyType, mentions=[])


@pytest.mark.asyncio
@pytest.mark.parametrize("httpx_mock, statusCode, replyType", [
    (None, HTTP_201_CREATED, "You are now subscribed to"),
    (None, HTTP_204_NO_CONTENT, "You are no longer subscribed to")
], indirect=["httpx_mock"])
async def test_subscribe(httpx_mock, statusCode, replyType):
    missionId = 900
    userId = memberNoRole.user.id

    httpx_mock.add_response(
        method="POST",
        url=f"{ARCHUB_URL}/missions/{missionId}/subscribe?discord_id={userId}",
        status_code=statusCode,
        match_headers=ARCHUB_HEADERS
    )

    interaction = Interaction(**MockRequest("subscribe", memberNoRole, options=[
        Option(value=missionId, name="subscribe", type=OptionType.INTEGER)]))
    reply = await handle_interaction(interaction)
    expected = f"{replyType} https://arcomm.co.uk/hub/missions/{missionId}"

    assert reply == ImmediateReply(expected, mentions=[])


@pytest.mark.asyncio
async def test_ticket(httpx_mock):
    createdUrl = "https://github.com/ARCOMM/ArcommBot/issues/64"

    httpx_mock.add_response(
        method="POST",
        url=f"https://api.github.com/repos/TomBurch/SvenBot/issues",
        json={"html_url": createdUrl},
        status_code=HTTP_201_CREATED,
        match_headers=GITHUB_HEADERS
    )

    options = [
        Option(value="TomBurch/SvenBot", name="repo", type=OptionType.STRING),
        Option(value="Test title", name="title", type=OptionType.STRING),
        Option(value="Test body", name="body", type=OptionType.STRING)
    ]
    interaction = Interaction(**MockRequest("ticket", memberNoRole, options=options))
    reply = await handle_interaction(interaction)
    expected = f"Ticket created at: {createdUrl}"

    assert reply == ImmediateReply(expected, mentions=[])


@pytest.mark.asyncio
@pytest.mark.parametrize("httpx_mock, coin", [
    (None, 'Heads'),
    (None, 'Tails')
], indirect=["httpx_mock"])
async def test_cointoss(httpx_mock, coin):
    interaction = Interaction(**MockRequest("cointoss", memberNoRole))

    with mock.patch.object(random, 'choice') as m:
        m.return_value = coin
        reply = await handle_interaction(interaction)
        assert (reply == ImmediateReply(coin))


@pytest.mark.asyncio
@pytest.mark.parametrize("httpx_mock, role, newName, patches, replyType", [
    (None, testRole, "RandomName", True, "was renamed"),
    (None, invalidRole, "RandomName", False, "is restricted"),
    (None, testRole, invalidRole["name"], False, "already exists")
], indirect=["httpx_mock"])
async def test_renamerole(httpx_mock, role, newName, patches, replyType):
    roleId = role["id"]

    httpx_mock.add_response(
        method="GET",
        url=f"{GUILD_URL}/{arcommGuild}/roles",
        json=roles,
        status_code=HTTP_200_OK
    )

    if patches:
        httpx_mock.add_response(
            method="PATCH",
            url=f"{GUILD_URL}/{arcommGuild}/roles/{roleId}",
            status_code=HTTP_200_OK,
        )

    interaction = Interaction(
        **MockRequest("renamerole", memberNoRole, options=[Option(value=roleId, name="role", type=OptionType.ROLE),
                                                           Option(value=newName, name="name", type=OptionType.STRING)]))
    reply = await handle_interaction(interaction)

    if newName == invalidRole["name"]:
        roleId = invalidRole['id']
        assert reply == ImmediateReply(f"<@&{roleId}> {replyType}", mentions=[])
    else:
        assert reply == ImmediateReply(f"<@&{roleId}> {replyType}", mentions=[])


if __name__ == "__main__":
    pytest.main()
