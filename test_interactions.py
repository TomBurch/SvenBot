import unittest
import responses
import werkzeug.exceptions as exceptions

from main import handle_interaction
from discord_interactions import InteractionType, InteractionResponseType

def callMatchesResponse(call, response):
    return call.request.method == response.method and call.request.url == response.url and call.response.status_code == response.status

class Reply(dict):
    def __init__(self, _type, content, mentions = None):
        if mentions is not None:
            dict.__init__(self, type = _type, data = {"content": content, "allowed_mentions": {"parse": mentions}})
        else:
            dict.__init__(self, type = _type, data = {"content": content})

class Member(dict):
    def __init__(self, id, name, roles = []):
        dict.__init__(self, user = {"id": id, "username": name}, roles = roles)

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
        self.memberWithRole = Member("User123", "TestUser", ["Role456"])
        self.memberNoRole = Member("User234", "TestUser2")

    def test_ping(self):
        result = handle_interaction(Interaction("ping", self.memberNoRole))
        expected = {
            'type': InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE, 
            'data': {'content': 'Pong!'}
        }
        self.assertEqual(result, expected)

    @responses.activate
    def test_role_withRole(self):
        userId = self.memberWithRole["user"]["id"]
        role = self.memberWithRole["roles"][0]

        expectedReply = Reply(
            InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
            f"<@{userId}> You've left <@&{role}>",
            ["users"]
        )

        successLeave = responses.Response(
            method = responses.DELETE,
            url = f"https://discord.com/api/v8/guilds/Guild123/members/{userId}/roles/{role}",
            status = 204
        )
        responses.add(successLeave)

        interaction = Interaction("role", self.memberWithRole, options = [{"value": role}])
        reply = handle_interaction(interaction)

        assert callMatchesResponse(responses.calls[0], successLeave)
        self.assertEqual(reply, expectedReply)

    @responses.activate
    def test_role_withNoRole(self):
        userId = self.memberNoRole["user"]["id"]
        role = self.memberWithRole["roles"][0]

        expectedReply = Reply(
            InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
            f"<@{userId}> You've joined <@&{role}>",
            ["users"]
        )

        successJoin = responses.Response(
            method = responses.PUT,
            url = f"https://discord.com/api/v8/guilds/Guild123/members/{userId}/roles/{role}",
            status = 204
        )
        responses.add(successJoin)

        interaction = Interaction("role", self.memberNoRole, options = [{"value": role}])
        reply = handle_interaction(interaction)

        assert callMatchesResponse(responses.calls[0], successJoin)
        self.assertEqual(reply, expectedReply)

    @responses.activate
    def test_role_restrictedWithRole(self):
        userId = self.memberWithRole["user"]["id"]
        role = self.memberWithRole["roles"][0]

        expectedReply = Reply(
            InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
            f"<@{userId}> Role <@&{role}> is restricted",
            ["users"]
        )

        failedLeave = responses.Response(
            method = responses.DELETE,
            url = f"https://discord.com/api/v8/guilds/Guild123/members/{userId}/roles/{role}",
            status = 403
        )
        responses.add(failedLeave)

        interaction = Interaction("role", self.memberWithRole, options = [{"value": role}])
        reply = handle_interaction(interaction)

        assert callMatchesResponse(responses.calls[0], failedLeave)
        self.assertEqual(reply, expectedReply)

    @responses.activate
    def test_role_restrictedWithNoRole(self):
        userId = self.memberNoRole["user"]["id"]
        role = self.memberWithRole["roles"][0]

        expectedReply = Reply(
            InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
            f"<@{userId}> Role <@&{role}> is restricted",
            ["users"]
        )

        failedJoin = responses.Response(
            method = responses.PUT,
            url = f"https://discord.com/api/v8/guilds/Guild123/members/{userId}/roles/{role}",
            status = 403
        )
        responses.add(failedJoin)

        interaction = Interaction("role", self.memberNoRole, options = [{"value": role}])
        reply = handle_interaction(interaction)

        assert callMatchesResponse(responses.calls[0], failedJoin)
        self.assertEqual(reply, expectedReply)
    
    @responses.activate
    def test_members(self):
        userId = self.memberNoRole["user"]["id"]
        username = self.memberWithRole["user"]["username"]
        role = self.memberWithRole["roles"][0]

        expectedReply = Reply(
            InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
            f"```\n{username}\n```",
            []
        )

        successMembers = responses.Response(
            method = responses.GET,
            url = "https://discord.com/api/v8/guilds/Guild123/members",
            status = 204,
            json = [self.memberWithRole]
        )
        responses.add(successMembers)

        interaction = Interaction("members", self.memberNoRole, options = [{"value": role}])
        reply = handle_interaction(interaction)

        assert callMatchesResponse(responses.calls[0], successMembers)
        self.assertEqual(reply, expectedReply)

if __name__ == "__main__":
    unittest.main()