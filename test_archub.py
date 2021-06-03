from starlette.status import HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST
import pytest

from main import handle_archub

ARCHUB_CHANNEL = 703618484386398349

MOCK_MISSION = "Made Up Mission"
MOCK_MISSIONID = 258
MOCK_AUTHOR = "AuthorName"
MOCK_AUTHORID = 7656198061366009
MOCK_ACTOR = "ActorName"
MOCK_ACTORID = 123456789012345
MOCK_URL = "http://www.url.com"

@pytest.mark.asyncio
@pytest.mark.parametrize("httpx_mock, endpoint, status, content", [
                        (None, "publish", HTTP_204_NO_CONTENT, f'**{MOCK_AUTHOR}** has published a new mission called **{MOCK_MISSION}**\\n{MOCK_URL}'),
                        (None, "note", HTTP_204_NO_CONTENT, f'**{MOCK_ACTOR}** has added a note to **{MOCK_MISSION}**\\n{MOCK_URL}'),
                        (None, "comment", HTTP_204_NO_CONTENT, f'**{MOCK_ACTOR}** has commented on **{MOCK_MISSION}**\\n{MOCK_URL}'),
                        (None, "verify", HTTP_204_NO_CONTENT, f'**{MOCK_ACTOR}** has verified **{MOCK_MISSION}**\\n'),
                        (None, "update", HTTP_204_NO_CONTENT, f'**{MOCK_ACTOR}** has updated **{MOCK_MISSION}**\\n{MOCK_URL}'),
                        (None, "fakeendpoint", HTTP_400_BAD_REQUEST, f'**fakeendpoint** is not a valid archub endpoint')
                        ], indirect=["httpx_mock"])
async def test_known_endpoints(httpx_mock, endpoint, status, content):
    httpx_mock.add_response(
        method = "POST",
        url = f"https://discord.com/api/v8/channels/{ARCHUB_CHANNEL}/messages",
        status_code = 200,
        match_content = f'{{\"content\": \"{content}\"}}'.encode()
    )

    options = {
        "mission": MOCK_MISSION,
        "missionId": MOCK_MISSIONID,
        "author": MOCK_AUTHOR,
        "authorId": MOCK_AUTHORID,
        "actor": MOCK_ACTOR,
        "actorId": MOCK_ACTORID,
        "url": MOCK_URL,
    }

    reply = await handle_archub(endpoint, options)
    assert reply == status

if __name__ == "__main__":
    pytest.main()
