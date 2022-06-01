import pytest
from starlette.status import HTTP_200_OK

from SvenBot.main import a3sync_task, recruit_task
from SvenBot.models import ResponseData
from SvenBot.utility import ADMIN_ROLE, CHANNELS_URL, STAFF_CHANNEL


@pytest.mark.asyncio
async def test_recruit_task(httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url=f"{CHANNELS_URL}/{STAFF_CHANNEL}/messages",
        status_code=HTTP_200_OK
    )

    reply = await recruit_task()
    expected = ResponseData(content=f"<@&{ADMIN_ROLE}> Post recruitment on <https://www.reddit.com/r/FindAUnit>",
                            allowed_mentions={'parse': ["roles"]})

    assert reply == expected


# @pytest.mark.asyncio
# async def test_a3sync_task():
#     reply = await a3sync_task()
#     expected = ResponseData(content=f"",
#                             allowed_mentions={'parse': []})
#
#     assert reply == expected


if __name__ == "__main__":
    pytest.main()
