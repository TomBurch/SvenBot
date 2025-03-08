import logging
import random

import d20
from fastapi import HTTPException
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_501_NOT_IMPLEMENTED,
)

from SvenBot import utility
from SvenBot.config import (
    ARCHUB_API,
    ARCHUB_HEADERS,
    GITHUB_HEADERS,
    GUILD_URL,
    HUB_URL,
)
from SvenBot.models import Interaction, InteractionResponse, InteractionType

gunicorn_logger = logging.getLogger("gunicorn.error")


async def execute_role(interaction: Interaction) -> str:
    guild_id = interaction.guild_id
    user_id = interaction.member.user.id
    (role_id,) = interaction.data.options

    if not await utility.validate_role_by_id(guild_id, role_id.value):
        return f"<@&{role_id.value}> is restricted"

    url = f"{GUILD_URL}/{guild_id}/members/{user_id}/roles/{role_id.value}"

    if role_id.value in interaction.member.roles:
        r = await utility.delete([HTTP_204_NO_CONTENT, HTTP_403_FORBIDDEN], url)
        reply = f"You've left <@&{role_id.value}>"
    else:
        r = await utility.put([HTTP_204_NO_CONTENT, HTTP_403_FORBIDDEN], url)
        reply = f"You've joined <@&{role_id.value}>"

    if r.status_code == HTTP_403_FORBIDDEN:
        return f"<@&{role_id.value}> is restricted"
    return reply


async def execute_roles(interaction: Interaction) -> str:
    guild_id = interaction.guild_id
    roles = await utility.get_roles(guild_id)

    joinable_roles = [role["name"] for role in roles if await utility.validate_role(guild_id, role, roles)]
    joinable_roles = sorted(joinable_roles)
    return "```\n{}\n```".format("\n".join(joinable_roles))


async def execute_members(interaction: Interaction) -> str:
    guild_id = interaction.guild_id
    (role_id,) = interaction.data.options

    url = f"{GUILD_URL}/{guild_id}/members"

    r = await utility.get([HTTP_200_OK], url, params={"limit": 200})
    members = r.json()
    reply = ""

    for member in members:
        if role_id.value in member["roles"]:
            reply += member["user"]["username"] + "\n"

    return f"```\n{reply}```"


async def execute_myroles(interaction: Interaction) -> str:
    reply = ""

    for role_id in interaction.member.roles:
        reply += f"<@&{role_id}>\n"

    return reply


async def execute_optime(interaction: Interaction) -> str:
    modifier = 0
    if interaction.data.options is not None and len(interaction.data.options) > 0:
        modifier = interaction.data.options[0].value

    if modifier == 0:
        modifier_string = ""
    elif modifier > 0:
        modifier_string = f" +{modifier}"
    else:
        modifier_string = f" {modifier}"

    time_until_optime = utility.time_until_optime(modifier)
    return f"Optime{modifier_string} starts in {time_until_optime}!"


async def execute_addrole(interaction: Interaction) -> str:
    guild_id = interaction.guild_id
    (name,) = interaction.data.options

    existing_role = await utility.find_role_by_name(guild_id, name.value, exclude_reserved=False)
    if existing_role is not None:
        role_id = existing_role["id"]
        return f"<@&{role_id}> already exists"

    url = f"{GUILD_URL}/{guild_id}/roles"
    r = await utility.post([HTTP_200_OK], url, json={"name": name.value, "mentionable": True})
    role_id = r.json()["id"]

    return f"<@&{role_id}> added"


async def execute_removerole(interaction: Interaction) -> str:
    guild_id = interaction.guild_id
    (role_id,) = interaction.data.options

    if await utility.validate_role_by_id(guild_id, role_id.value):
        url = f"{GUILD_URL}/{guild_id}/roles/{role_id.value}"

        await utility.delete([HTTP_204_NO_CONTENT], url)
        return "Role deleted"

    return "Role is restricted"


async def execute_ticket(interaction: Interaction) -> str:
    member = interaction.member
    repo, title, body = interaction.data.options
    username = member.user.username if (member.nick is None) else member.nick
    json = {"title": f"{username}: {title.value}", "body": body.value}

    repo_url = f"https://api.github.com/repos/{repo.value}/issues"
    r = await utility.post([HTTP_201_CREATED], repo_url, json=json, headers=GITHUB_HEADERS)
    created_url = r.json()["html_url"]

    return f"Ticket created at: {created_url}"


async def execute_cointoss(interaction: Interaction) -> str:  # noqa: ARG001
    return random.choice(["Heads", "Tails"])


async def execute_d20(interaction: Interaction) -> str:
    (roll_str,) = interaction.data.options
    return str(d20.roll(roll_str.value))


async def execute_renamerole(interaction: Interaction) -> str:
    guild_id = interaction.guild_id
    role_id, new_name = interaction.data.options
    if not await utility.validate_role_by_id(guild_id, role_id.value):
        return f"<@&{role_id.value}> is restricted"

    existing_role = await utility.find_role_by_name(guild_id, new_name.value, exclude_reserved=False)
    if existing_role is not None:
        role_id = existing_role["id"]
        return f"<@&{role_id}> already exists"

    url = f"{GUILD_URL}/{guild_id}/roles/{role_id.value}"
    await utility.patch([HTTP_200_OK], url, json={"name": new_name.value})

    return f"<@&{role_id.value}> was renamed"


async def execute_maps(interaction: Interaction) -> str:  # noqa: ARG001
    url = f"{ARCHUB_API}/maps"
    r = await utility.get([HTTP_200_OK], url, headers=ARCHUB_HEADERS)
    maps = r.json()

    out_string = "File name [Display name]\n=========================\n"
    for _map in maps:
        out_string += (
            f"{_map['class_name']}\n"
            if _map["class_name"] == _map["display_name"]
            else f"{_map['class_name']} [{_map['display_name']}]\n"
        )

    return f"```ini\n{out_string}```"


async def execute_renamemap(interaction: Interaction) -> str:
    old_name, new_name = interaction.data.options

    url = f"{ARCHUB_API}/maps?old_name={old_name.value}&new_name={new_name.value}"
    await utility.patch([HTTP_204_NO_CONTENT], url, headers=ARCHUB_HEADERS)

    return f"`{old_name.value}` was renamed to `{new_name.value}`"


async def execute_subscribe(interaction: Interaction) -> str:
    user_id = interaction.member.user.id
    (mission_id,) = interaction.data.options
    url = f"{ARCHUB_API}/missions/{mission_id.value}/subscribe?discord_id={user_id}"
    r = await utility.post([HTTP_201_CREATED, HTTP_204_NO_CONTENT], url, headers=ARCHUB_HEADERS)
    mission_url = f"{HUB_URL}/missions/{mission_id.value}"

    if r.status_code == HTTP_201_CREATED:
        return f"You are now subscribed to {mission_url}"

    return f"You are no longer subscribed to {mission_url}"


async def execute_ping(interaction: Interaction) -> str:  # noqa: ARG001
    return "Pong!"


execute_map = {
    "addrole": execute_addrole,
    "cointoss": execute_cointoss,
    "d20": execute_d20,
    "maps": execute_maps,
    "members": execute_members,
    "myroles": execute_myroles,
    "optime": execute_optime,
    "ping": execute_ping,
    "removerole": execute_removerole,
    "renamemap": execute_renamemap,
    "renamerole": execute_renamerole,
    "role": execute_role,
    "roles": execute_roles,
    "subscribe": execute_subscribe,
    "ticket": execute_ticket,
}

ephemeral = ["myroles"]


async def handle_interaction(interaction: Interaction) -> InteractionResponse:
    if interaction.type != InteractionType.APPLICATION_COMMAND:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Not an application command")

    command = interaction.data.name
    if command not in execute_map:
        raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail=f"'{command}' is not a known command")

    try:
        gunicorn_logger.info(f"'{interaction.member.user.username}' executing '{command}'")

        reply = await execute_map[command](interaction)
        return utility.immediate_reply(reply, ephemeral=command in ephemeral)

    except Exception as e:
        gunicorn_logger.error(f"Error executing '{command}':\n{e})")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error executing '{command}'") from e
