import unittest
import responses
import werkzeug.exceptions as exceptions

from main import handle_interaction
from discord_interactions import InteractionType, InteractionResponseType

class Interaction():
    def __init__(self, name, options = []):
        self.json = {
            "type": InteractionType.APPLICATION_COMMAND,
            "member": {
                "user": {
                    "id": "User123" 
                },
                "roles": []
            },
            "data": {
                "name": name,
                "options": options
            }
        }

class TestInteractions(unittest.TestCase):
    def test_ping(self):
        result = handle_interaction(Interaction("ping"))
        expected = {
            'type': InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE, 
            'data': {'content': 'Pong!'}
        }
        self.assertEqual(result, expected)

    @responses.activate
    def test_role(self):
        user = "User123"
        role = "Role456"

        responses.add(**{
            "method": responses.PUT,
            "url": f"https://discord.com/api/v8/guilds/None/members/{user}/roles/{role}"
        })
        responses.add(**{
            "method": responses.DELETE,
            "url": f"https://discord.com/api/v8/guilds/None/members/{user}/roles/{role}"
        })

        interaction = Interaction("role", options = [{"value": role}])

        r = handle_interaction(interaction)
        self.assertEqual(responses.calls[0].request.method, responses.PUT)
        self.assertEqual(responses.calls[0].request.url, "https://discord.com/api/v8/guilds/None/members/User123/roles/Role456")
        self.assertEqual(r.get("type"), InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE)
        self.assertEqual(r.get("data").get("content"), f"<@{user}> You have joined <@&{role}>")
        self.assertEqual(r.get("data").get("allowed_mentions").get("parse"), ["users"])

        interaction.json["member"]["roles"] = [role]

        r = handle_interaction(interaction)
        self.assertEqual(responses.calls[1].request.method, responses.DELETE)
        self.assertEqual(responses.calls[1].request.url, "https://discord.com/api/v8/guilds/None/members/User123/roles/Role456")
        self.assertEqual(r.get("type"), InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE)
        self.assertEqual(r.get("data").get("content"), f"<@{user}> You have left <@&{role}>")
        self.assertEqual(r.get("data").get("allowed_mentions").get("parse"), ["users"])

        interaction.json["member"]["roles"] = []
        

if __name__ == "__main__":
    unittest.main()