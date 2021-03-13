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
                "roles": ["Role456"]
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
        responses.add(**{
            "method": responses.PUT,
            "url": "https://discord.com/api/v8/guilds/None/members/User123/roles/Role456"
        })
        responses.add(**{
            "method": responses.DELETE,
            "url": "https://discord.com/api/v8/guilds/None/members/User123/roles/Role456"
        })

        interaction = Interaction("role", options = [{"value": "Role456"}])
        handle_interaction(interaction)
        self.assertEqual(responses.calls[0].request.method, responses.DELETE)
        self.assertEqual(responses.calls[0].request.url, "https://discord.com/api/v8/guilds/None/members/User123/roles/Role456")

        interaction.json["member"]["roles"] = []
        handle_interaction(interaction)
        self.assertEqual(responses.calls[1].request.method, responses.PUT)
        self.assertEqual(responses.calls[1].request.url, "https://discord.com/api/v8/guilds/None/members/User123/roles/Role456")

if __name__ == "__main__":
    unittest.main()