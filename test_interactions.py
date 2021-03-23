import unittest
import os
from datetime import datetime

from sanic import exceptions
from httpx import Response
import pytest

from main import handle_interaction, execute_optime
from utility import InteractionType, ImmediateReply, clearMemoizeCache, CLIENT_ID

class Member(dict):
    def __init__(self, id, name, roles = []):
        dict.__init__(self, user = {"id": id, "username": name}, roles = roles)

class Role(dict):
    def __init__(self, id, name, position, color = 0, botId = None):
        if botId is not None:
            dict.__init__(self, id = id, name = name, position = position, color = color, tags = {"bot_id": botId})
        else:
            dict.__init__(self, id = id, name = name, position = position, color = color)

class Interaction():
    def __init__(self, name, member = None, options = []):
        self.json = {
            "type": InteractionType.APPLICATION_COMMAND,
            "member": member,
            "data": {
                "name": name,
                "options": options
            },
            "guild_id" : "342006395010547712"
        }

botRole = Role("SvenBotRoleId", "SvenBot", 3, botId = CLIENT_ID)
invalidRole = Role("RoleId789", "InvalidRole", 1, color = 10)
testRole = Role("RoleId456", "TestRole", 2)

roles = [botRole, testRole, invalidRole]
arcommGuild = "342006395010547712"

memberNoRole = Member("User234", "TestUser2")
memberWithRole = Member("User123", "TestUser", [testRole["id"]])

@pytest.fixture(autouse = True)
def setUp():
    clearMemoizeCache()

@pytest.mark.asyncio
async def test_ping():
    reply = await handle_interaction(Interaction("ping", memberNoRole))
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
    userId = user["user"]["id"]
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

    interaction = Interaction("role", user, options = [{"value": roleId}])
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

    interaction = Interaction("roles", memberWithRole)
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

    with pytest.raises(exceptions.NotFound) as e2:
        with pytest.raises(RuntimeError) as e1:
            interaction = Interaction("roles", memberNoRole)
            reply = await handle_interaction(interaction)
        assert e1.match("Unable to find bot's role")
    assert e2.match("Error executing 'roles'")

@pytest.mark.asyncio
async def test_members(httpx_mock):
    roleId = testRole["id"]

    httpx_mock.add_response(
        method = "GET",
        url = f"https://discord.com/api/v8/guilds/{arcommGuild}/members?limit=200",
        json = [memberWithRole],
        status_code = 200
    )

    interaction = Interaction("members", memberNoRole, options = [{"value": roleId}])
    reply = await handle_interaction(interaction)

    username = memberWithRole["user"]["username"]
    assert reply == ImmediateReply(f"```\n{username}\n```", mentions = [])

@pytest.mark.asyncio
async def test_myroles(httpx_mock):
    userId = memberWithRole["user"]["id"]

    interaction = Interaction("myroles", memberWithRole)
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

    interaction = Interaction("optime", memberNoRole)
    await handle_interaction(interaction)

if __name__ == "__main__":
    pytest.main()
