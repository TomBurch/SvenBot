import unittest
import responses
import werkzeug.exceptions as exceptions
from dotenv import load_dotenv
import os
from datetime import datetime
import pytest

from main import handle_interaction, execute_optime
from discord_interactions import InteractionType
from utility import ImmediateReply, clearMemoizeCache

load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")

def assert_callMatchesResponse(call, response):
    assert call.request.method == response.method
    assert call.request.url == response.url
    assert call.response.status_code == response.status

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

class TestInteractions(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.botRole = Role("SvenBotRoleId", "SvenBot", 3, botId = CLIENT_ID)
        self.testRole = Role("RoleId456", "TestRole", 2)
        self.invalidRole = Role("RoleId789", "InvalidRole", 1, color = 10)
        self.roles = [self.botRole, self.testRole, self.invalidRole]

        self.arcommGuild = "342006395010547712"

        self.memberWithRole = Member("User123", "TestUser", [self.testRole["id"]])
        self.memberNoRole = Member("User234", "TestUser2")

    def setUp(self):
        clearMemoizeCache()

    def test_ping(self):
        result = handle_interaction(Interaction("ping", self.memberNoRole))
        expected = ImmediateReply("Pong!")

        self.assertEqual(result, expected)

    @responses.activate
    def test_role_withRole(self):
        userId = self.memberWithRole["user"]["id"]
        roleId = self.testRole["id"]

        expectedReply = ImmediateReply(f"<@{userId}> You've left <@&{roleId}>", mentions = ["users"])

        successLeave = responses.Response(
            method = responses.DELETE,
            url = f"https://discord.com/api/v8/guilds/{self.arcommGuild}/members/{userId}/roles/{roleId}",
            status = 204
        )
        responses.add(successLeave)
        responses.add(responses.GET, f"https://discord.com/api/v8/guilds/{self.arcommGuild}/roles", json = self.roles, status = 200)

        interaction = Interaction("role", self.memberWithRole, options = [{"value": roleId}])
        reply = handle_interaction(interaction)

        assert_callMatchesResponse(responses.calls[1], successLeave)
        self.assertEqual(reply, expectedReply)

    @responses.activate
    def test_role_withNoRole(self):
        userId = self.memberNoRole["user"]["id"]
        roleId = self.testRole["id"]

        expectedReply = ImmediateReply(f"<@{userId}> You've joined <@&{roleId}>", mentions = ["users"])

        successJoin = responses.Response(
            method = responses.PUT,
            url = f"https://discord.com/api/v8/guilds/{self.arcommGuild}/members/{userId}/roles/{roleId}",
            status = 204
        )
        responses.add(successJoin)
        responses.add(responses.GET, f"https://discord.com/api/v8/guilds/{self.arcommGuild}/roles", json = self.roles, status = 200)

        interaction = Interaction("role", self.memberNoRole, options = [{"value": roleId}])
        reply = handle_interaction(interaction)

        assert_callMatchesResponse(responses.calls[1], successJoin)
        self.assertEqual(reply, expectedReply)

    @responses.activate
    def test_role_restrictedWithRole(self):
        userId = self.memberWithRole["user"]["id"]
        roleId = self.testRole["id"]

        expectedReply = ImmediateReply(f"<@{userId}> Role <@&{roleId}> is restricted", mentions = ["users"])

        failedLeave = responses.Response(
            method = responses.DELETE,
            url = f"https://discord.com/api/v8/guilds/{self.arcommGuild}/members/{userId}/roles/{roleId}",
            status = 403
        )
        responses.add(failedLeave)
        responses.add(responses.GET, f"https://discord.com/api/v8/guilds/{self.arcommGuild}/roles", json = self.roles, status = 200)

        interaction = Interaction("role", self.memberWithRole, options = [{"value": roleId}])
        reply = handle_interaction(interaction)

        assert_callMatchesResponse(responses.calls[1], failedLeave)
        self.assertEqual(reply, expectedReply)

    @responses.activate
    def test_role_restrictedWithNoRole(self):
        userId = self.memberNoRole["user"]["id"]
        roleId = self.testRole["id"]

        expectedReply = ImmediateReply(f"<@{userId}> Role <@&{roleId}> is restricted", mentions = ["users"])

        failedJoin = responses.Response(
            method = responses.PUT,
            url = f"https://discord.com/api/v8/guilds/{self.arcommGuild}/members/{userId}/roles/{roleId}",
            status = 403
        )
        responses.add(failedJoin)
        responses.add(responses.GET, f"https://discord.com/api/v8/guilds/{self.arcommGuild}/roles", json = self.roles, status = 200)

        interaction = Interaction("role", self.memberNoRole, options = [{"value": roleId}])
        reply = handle_interaction(interaction)

        assert_callMatchesResponse(responses.calls[1], failedJoin)
        self.assertEqual(reply, expectedReply)
    
    @responses.activate
    def test_role_failedValidation(self):
        userId = self.memberNoRole["user"]["id"]
        roleId = self.invalidRole["id"]

        expectedReply = ImmediateReply(f"<@{userId}> Role <@&{roleId}> is restricted", mentions = ["users"])

        responses.add(responses.GET, f"https://discord.com/api/v8/guilds/{self.arcommGuild}/roles", json = self.roles, status = 200)

        interaction = Interaction("role", self.memberNoRole, options = [{"value": roleId}])
        reply = handle_interaction(interaction)

        self.assertEqual(reply, expectedReply)
    
    @responses.activate
    def test_roles(self):
        role = self.testRole

        expectedReply = ImmediateReply("```\nTestRole\n```".format(self.botRole["name"], role["name"]), mentions = [])

        successRoles = responses.Response(
            method = responses.GET,
            url = f"https://discord.com/api/v8/guilds/{self.arcommGuild}/roles",
            status = 200,
            json = [self.testRole, self.botRole]
        )
        responses.add(successRoles)

        interaction = Interaction("roles", self.memberWithRole)
        reply = handle_interaction(interaction)

        assert_callMatchesResponse(responses.calls[0], successRoles)
        self.assertEqual(reply, expectedReply)

    @responses.activate
    def test_rolesNoBotRole(self):
        expectedReply = ImmediateReply("ERROR: Unable to find bot's role", mentions = [])

        successRoles = responses.Response(
            method = responses.GET,
            url = f"https://discord.com/api/v8/guilds/{self.arcommGuild}/roles",
            status = 200,
            json = [self.testRole]
        )
        responses.add(successRoles)

        with pytest.raises(exceptions.NotFound) as e2:
            with pytest.raises(RuntimeError) as e1:
                interaction = Interaction("roles", self.memberNoRole)
                reply = handle_interaction(interaction)

                assert_callMatchesResponse(responses.calls[0], successRoles)
                self.assertEqual(reply, expectedReply)

            assert e1.match("Unable to find bot's role")
        assert e2.match("Error executing 'roles'")

    @responses.activate
    def test_members(self):
        userId = self.memberNoRole["user"]["id"]
        username = self.memberWithRole["user"]["username"]
        role = self.memberWithRole["roles"][0]

        expectedReply = ImmediateReply(f"```\n{username}\n```", mentions = [])

        successMembers = responses.Response(
            method = responses.GET,
            url = f"https://discord.com/api/v8/guilds/{self.arcommGuild}/members?limit=200",
            status = 200,
            json = [self.memberWithRole]
        )
        responses.add(successMembers)

        interaction = Interaction("members", self.memberNoRole, options = [{"value": role}])
        reply = handle_interaction(interaction)

        assert_callMatchesResponse(responses.calls[0], successMembers)
        self.assertEqual(reply, expectedReply)

    def test_myroles(self):
        userId = self.memberWithRole["user"]["id"]
        role = self.memberWithRole["roles"][0]

        expectedReply = ImmediateReply(f"<@&{role}>\n", mentions = [], ephemeral = True)

        interaction = Interaction("myroles", self.memberWithRole)
        reply = handle_interaction(interaction)
        self.assertEqual(reply, expectedReply)

    def test_optime(self):
        self.assertEqual(execute_optime(datetime(2021, 3, 19, 15, 30), 0), "Optime starts in 2:30:00!")
        self.assertEqual(execute_optime(datetime(2021, 3, 19, 19, 30, 42), 0), "Optime starts in 22:29:18!")
        self.assertEqual(execute_optime(datetime(2021, 3, 19, 18, 0, 0), 0), "Optime starts in 0:00:00!")
        self.assertEqual(execute_optime(datetime(2021, 3, 19, 18, 0, 0), 1), "Optime +1 starts in 1:00:00!")
        self.assertEqual(execute_optime(datetime(2021, 3, 19, 18, 0, 0), -1), "Optime -1 starts in 23:00:00!")
        self.assertEqual(execute_optime(datetime(2021, 3, 19, 18, 0, 0), 7), "Optime modifier is too large")

        interaction = Interaction("optime", self.memberNoRole)
        handle_interaction(interaction)

if __name__ == "__main__":
    unittest.main()
