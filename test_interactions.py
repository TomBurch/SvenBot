from datetime import datetime

from fastapi import HTTPException
import pytest

from main import handle_interaction, execute_optime
from models import Interaction, Member, Option, OptionType, InteractionType
from utility import ARCHUB_HEADERS, ImmediateReply, CLIENT_ID

class Role(dict):
    def __init__(self, id, name, position, color = 0, botId = None):
        if botId is not None:
            dict.__init__(self, id = id, name = name, position = position, color = color, tags = {"bot_id": botId})
        else:
            dict.__init__(self, id = id, name = name, position = position, color = color)

class MockRequest(dict):
    def __init__(self, name, member = None, options = []):
        dict.__init__(self, type = InteractionType.APPLICATION_COMMAND, member = member, data = {"name": name, "options": options, "id": "MockCommandId"}, 
                    guild_id = "342006395010547712", version = 1, token = "MockToken", application_id = "MockAppId", id = "MockRequestId")

botRole = Role("SvenBotRoleId", "SvenBot", 3, botId = CLIENT_ID)
invalidRole = Role("RoleId789", "InvalidRole", 1, color = 10)
testRole = Role("RoleId456", "TestRole", 2)
roleNotInGuild = Role("RoleId123", "RoleNotInGuild", 5)

roles = [botRole, testRole, invalidRole]
arcommGuild = "342006395010547712"

memberNoRole = Member(user = {"id": "User234", "username": "TestUser2", "discriminator": "4042"}, roles = [])
memberWithRole = Member(user = {"id": "User123", "username": "TestUser", "discriminator": "3124"}, roles = [testRole["id"]])

@pytest.mark.asyncio
async def test_ping():
    interaction = Interaction(**MockRequest("ping", memberNoRole))
    reply = await handle_interaction(interaction)
    expected = ImmediateReply("Pong!")

    assert reply == expected

@pytest.mark.asyncio
@pytest.mark.parametrize("httpx_mock, user, role, roleMethod, roleStatus, replyType", [
                        (None, memberWithRole, testRole, "DELETE", 204, "Left"),
                        (None, memberNoRole, testRole, "PUT", 204, "Joined"),
                        (None, memberWithRole, testRole, "DELETE", 403, "Restricted"),
                        (None, memberNoRole, testRole, "PUT", 403, "Restricted"),
                        (None, memberWithRole, invalidRole, None, None, "Restricted"),
                        (None, memberNoRole, invalidRole, None, None, "Restricted")
                        ], indirect=["httpx_mock"])
async def test_role(httpx_mock, user, role, roleMethod, roleStatus, replyType):
    userId = user.user.id
    roleId = role["id"]

    httpx_mock.add_response(
        method = "GET",
        url = f"https://discord.com/api/v8/guilds/{arcommGuild}/roles",
        json = roles,
        status_code = 200
    )

    if roleMethod is not None:
        httpx_mock.add_response(     
            method = roleMethod,   
            url = f"https://discord.com/api/v8/guilds/{arcommGuild}/members/{userId}/roles/{roleId}",
            status_code = roleStatus
        )

    interaction = Interaction(**MockRequest("role", user, options = [Option(value = roleId, name = "role", type = OptionType.ROLE)]))
    reply = await handle_interaction(interaction)

    if replyType == "Left":
        assert reply == ImmediateReply(f"<@{userId}> You've left <@&{roleId}>", mentions = ["users"])
    elif replyType == "Joined":
        assert reply == ImmediateReply(f"<@{userId}> You've joined <@&{roleId}>", mentions = ["users"])
    elif replyType == "Restricted":
        assert reply == ImmediateReply(f"<@{userId}> Role <@&{roleId}> is restricted", mentions = ["users"])
    else:
        assert False
  
@pytest.mark.asyncio
async def test_roles(httpx_mock):
    httpx_mock.add_response(
        method = "GET",
        url = f"https://discord.com/api/v8/guilds/{arcommGuild}/roles",
        json = roles,
        status_code = 200
    )

    interaction = Interaction(**MockRequest("roles", memberWithRole))
    reply = await handle_interaction(interaction)

    assert reply == ImmediateReply("```\n{}\n```".format(testRole["name"]), mentions = [])

@pytest.mark.asyncio
async def test_rolesNoBotRole(httpx_mock):
    httpx_mock.add_response(
        method = "GET",
        url = f"https://discord.com/api/v8/guilds/{arcommGuild}/roles",
        json = [testRole, invalidRole],
        status_code = 200
    )

    with pytest.raises(HTTPException) as e2:
        with pytest.raises(RuntimeError, match = "Unable to find bot's role") as e1:
            interaction = Interaction(**MockRequest("roles", memberNoRole))
            reply = await handle_interaction(interaction)

@pytest.mark.asyncio
async def test_members(httpx_mock):
    roleId = testRole["id"]

    httpx_mock.add_response(
        method = "GET",
        url = f"https://discord.com/api/v8/guilds/{arcommGuild}/members?limit=200",
        json = [memberWithRole.dict()],
        status_code = 200
    )

    interaction = Interaction(**MockRequest("members", memberNoRole, options = [Option(value = roleId, name = "role", type = OptionType.ROLE)]))
    reply = await handle_interaction(interaction)

    username = memberWithRole.user.username
    assert reply == ImmediateReply(f"```\n{username}\n```", mentions = [])

@pytest.mark.asyncio
async def test_myroles():
    interaction = Interaction(**MockRequest("myroles", memberWithRole))
    reply = await handle_interaction(interaction)

    assert reply == ImmediateReply("<@&{}>\n".format(testRole["id"]), mentions = [], ephemeral = True)

@pytest.mark.asyncio
async def test_optime():
    assert execute_optime(datetime(2021, 3, 19, 15, 30), 0) == "Optime starts in 2:30:00!"
    assert execute_optime(datetime(2021, 3, 19, 19, 30, 42), 0) == "Optime starts in 22:29:18!"
    assert execute_optime(datetime(2021, 3, 19, 18, 0, 0), 0) == "Optime starts in 0:00:00!"
    assert execute_optime(datetime(2021, 3, 19, 18, 0, 0), 1) == "Optime +1 starts in 1:00:00!"
    assert execute_optime(datetime(2021, 3, 19, 18, 0, 0), -1) == "Optime -1 starts in 23:00:00!"
    assert execute_optime(datetime(2021, 3, 19, 18, 0, 0), 7) == "Optime modifier is too large"

    interaction = Interaction(**MockRequest("optime", memberNoRole))
    await handle_interaction(interaction)

@pytest.mark.asyncio
@pytest.mark.parametrize("httpx_mock, roleName, roleId, sendsPost, replyType", [
                        (None, "NewRole", "NewRoleId", True, "added"),
                        (None, "TestRole", "RoleId456", False, "already exists")
                        ], indirect=["httpx_mock"])
async def test_addrole(httpx_mock, roleName, roleId, sendsPost, replyType):
    httpx_mock.add_response(
        method = "GET",
        url = f"https://discord.com/api/v8/guilds/{arcommGuild}/roles",
        json = roles,
        status_code = 200
    )

    if sendsPost:
        httpx_mock.add_response(
            method = "POST",
            url = f"https://discord.com/api/v8/guilds/342006395010547712/roles",
            json = Role(roleId, roleName, 4),
            status_code = 200
        )

    interaction = Interaction(**MockRequest("addrole", memberNoRole, options = [Option(value = roleName, name = "name", type = OptionType.STRING)]))
    reply = await handle_interaction(interaction)

    assert reply == ImmediateReply(f"<@&{roleId}> {replyType}", mentions = [])

@pytest.mark.asyncio
@pytest.mark.parametrize("httpx_mock, role, sendsDelete, replyType", [
                        (None, testRole, True, "Role deleted"),
                        (None, invalidRole, False, "Role is restricted")
                        ], indirect=["httpx_mock"])
async def test_removerole(httpx_mock, role, sendsDelete, replyType):
    roleId = role["id"]

    httpx_mock.add_response(
        method = "GET",
        url = f"https://discord.com/api/v8/guilds/{arcommGuild}/roles",
        json = roles,
        status_code = 200
    )

    if sendsDelete:
        httpx_mock.add_response(
            method = "DELETE",
            url = f"https://discord.com/api/v8/guilds/342006395010547712/roles/{roleId}",
            status_code = 204
        )

    interaction = Interaction(**MockRequest("removerole", memberNoRole, options = [Option(value = roleId, name = "role", type = OptionType.ROLE)]))
    reply = await handle_interaction(interaction)

    assert reply == ImmediateReply(replyType, mentions = [])

@pytest.mark.asyncio
@pytest.mark.parametrize("httpx_mock, statusCode, replyType", [
                        (None, 201, "You are now subscribed to"),
                        (None, 204, "You are no longer subscribed to")
                        ], indirect=["httpx_mock"])
async def test_subscribe(httpx_mock, statusCode, replyType):
    missionId = 900
    userId = memberNoRole.user.id

    httpx_mock.add_response(
        method = "POST",
        url = f"https://arcomm.co.uk/api/v1/missions/{missionId}/subscribe?discord_id={userId}",
        status_code = statusCode,
        match_headers = ARCHUB_HEADERS
    )

    interaction = Interaction(**MockRequest("subscribe", memberNoRole, options = [Option(value = missionId, name = "subscribe", type = OptionType.INTEGER)]))
    reply = await handle_interaction(interaction)
    expected = f"{replyType} https://arcomm.co.uk/hub/missions/{missionId}"

    assert reply == ImmediateReply(expected, mentions = [])

if __name__ == "__main__":
    pytest.main()
