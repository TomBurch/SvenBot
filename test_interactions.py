import unittest
import responses
import werkzeug.exceptions as exceptions
from dotenv import load_dotenv
import os

from main import handle_interaction
from discord_interactions import InteractionType, InteractionResponseType
from utility import ImmediateReply

load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")

def callMatchesResponse(call, response):
    return call.request.method == response.method and call.request.url == response.url and call.response.status_code == response.status

class Member(dict):
    def __init__(self, id, name, roles = []):
        dict.__init__(self, user = {"id": id, "username": name}, roles = roles)

class Role(dict):
    def __init__(self, id, name, position, botId = None):
        if botId is not None:
            dict.__init__(self, id = id, name = name, position = position, tags = {"bot_id": botId})
        else:
            dict.__init__(self, id = id, name = name, position = position)

class Interaction():
    def __init__(self, name, member = None, options = []):
        self.json = {
            "type": InteractionType.APPLICATION_COMMAND,
            "member": member,
            "data": {
                "name": name,
                "options": options
            },
            "guild_id" : "Guild123"
        }

class TestInteractions(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.botRole = Role("SvenBotRoleId", "SvenBot", 2, CLIENT_ID)
        self.testRole = Role("RoleId456", "TestRole", 1)
        self.memberWithRole = Member("User123", "TestUser", [self.testRole["id"]])
        self.memberNoRole = Member("User234", "TestUser2")

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
            url = f"https://discord.com/api/v8/guilds/Guild123/members/{userId}/roles/{roleId}",
            status = 204
        )
        responses.add(successLeave)

        interaction = Interaction("role", self.memberWithRole, options = [{"value": roleId}])
        reply = handle_interaction(interaction)

        assert callMatchesResponse(responses.calls[0], successLeave)
        self.assertEqual(reply, expectedReply)

    @responses.activate
    def test_role_withNoRole(self):
        userId = self.memberNoRole["user"]["id"]
        roleId = self.testRole["id"]

        expectedReply = ImmediateReply(f"<@{userId}> You've joined <@&{roleId}>", mentions = ["users"])

        successJoin = responses.Response(
            method = responses.PUT,
            url = f"https://discord.com/api/v8/guilds/Guild123/members/{userId}/roles/{roleId}",
            status = 204
        )
        responses.add(successJoin)

        interaction = Interaction("role", self.memberNoRole, options = [{"value": roleId}])
        reply = handle_interaction(interaction)

        assert callMatchesResponse(responses.calls[0], successJoin)
        self.assertEqual(reply, expectedReply)

    @responses.activate
    def test_role_restrictedWithRole(self):
        userId = self.memberWithRole["user"]["id"]
        roleId = self.testRole["id"]

        expectedReply = ImmediateReply(f"<@{userId}> Role <@&{roleId}> is restricted", mentions = ["users"])

        failedLeave = responses.Response(
            method = responses.DELETE,
            url = f"https://discord.com/api/v8/guilds/Guild123/members/{userId}/roles/{roleId}",
            status = 403
        )
        responses.add(failedLeave)

        interaction = Interaction("role", self.memberWithRole, options = [{"value": roleId}])
        reply = handle_interaction(interaction)

        assert callMatchesResponse(responses.calls[0], failedLeave)
        self.assertEqual(reply, expectedReply)

    @responses.activate
    def test_role_restrictedWithNoRole(self):
        userId = self.memberNoRole["user"]["id"]
        roleId = self.testRole["id"]

        expectedReply = ImmediateReply(f"<@{userId}> Role <@&{roleId}> is restricted", mentions = ["users"])

        failedJoin = responses.Response(
            method = responses.PUT,
            url = f"https://discord.com/api/v8/guilds/Guild123/members/{userId}/roles/{roleId}",
            status = 403
        )
        responses.add(failedJoin)

        interaction = Interaction("role", self.memberNoRole, options = [{"value": roleId}])
        reply = handle_interaction(interaction)

        assert callMatchesResponse(responses.calls[0], failedJoin)
        self.assertEqual(reply, expectedReply)
    
    @responses.activate
    def test_roles(self):
        role = self.testRole

        expectedReply = ImmediateReply("```\n{}\n```".format(role["name"]), mentions = [])

        successRoles = responses.Response(
            method = responses.GET,
            url = f"https://discord.com/api/v8/guilds/Guild123/roles",
            status = 200,
            json = [self.testRole, self.botRole]
        )
        responses.add(successRoles)

        interaction = Interaction("roles", self.memberWithRole)
        reply = handle_interaction(interaction)

        assert callMatchesResponse(responses.calls[0], successRoles)
        self.assertEqual(reply, expectedReply)

    @responses.activate
    def test_rolesNoBotRole(self):
        expectedReply = ImmediateReply("ERROR: Unable to find bot's role", mentions = [])

        successRoles = responses.Response(
            method = responses.GET,
            url = f"https://discord.com/api/v8/guilds/Guild123/roles",
            status = 200,
            json = [self.testRole]
        )
        responses.add(successRoles)

        interaction = Interaction("roles", self.memberNoRole)
        reply = handle_interaction(interaction)

        assert callMatchesResponse(responses.calls[0], successRoles)
        self.assertEqual(reply, expectedReply)

    @responses.activate
    def test_members(self):
        userId = self.memberNoRole["user"]["id"]
        username = self.memberWithRole["user"]["username"]
        role = self.memberWithRole["roles"][0]

        expectedReply = ImmediateReply(f"```\n{username}\n```", mentions = [])

        successMembers = responses.Response(
            method = responses.GET,
            url = "https://discord.com/api/v8/guilds/Guild123/members?limit=200",
            status = 200,
            json = [self.memberWithRole]
        )
        responses.add(successMembers)

        interaction = Interaction("members", self.memberNoRole, options = [{"value": role}])
        reply = handle_interaction(interaction)

        assert callMatchesResponse(responses.calls[0], successMembers)
        self.assertEqual(reply, expectedReply)

    def test_myroles(self):
        userId = self.memberWithRole["user"]["id"]
        role = self.memberWithRole["roles"][0]

        expectedReply = ImmediateReply(f"<@&{role}>\n", mentions = [], ephemeral = True)

        interaction = Interaction("myroles", self.memberWithRole)
        reply = handle_interaction(interaction)
        self.assertEqual(reply, expectedReply)

if __name__ == "__main__":
    unittest.main()