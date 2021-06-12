import logging
from datetime import datetime, timedelta
from pytz import timezone

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.status import HTTP_200_OK, HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_501_NOT_IMPLEMENTED
import uvicorn

import utility
from utility import InteractionType, InteractionResponseType, GUILD_URL

async def execute_role(roles, role_id, guild_id, user_id):
    if not await utility.validateRoleById(guild_id, role_id):
        logging.warning(f"Role <@&{role_id}> is restricted (validation)")
        return f"<@{user_id}> Role <@&{role_id}> is restricted"
    
    url = f"{GUILD_URL}/{guild_id}/members/{user_id}/roles/{role_id}"

    if role_id in roles:
        r = await utility.delete([HTTP_204_NO_CONTENT, HTTP_403_FORBIDDEN], url)
        reply = f"<@{user_id}> You've left <@&{role_id}>"
    else:
        r = await utility.put([HTTP_204_NO_CONTENT, HTTP_403_FORBIDDEN], url)
        reply = f"<@{user_id}> You've joined <@&{role_id}>"

    if r.status_code == 403:
        logging.warning(f"Role <@&{role_id}> is restricted (403)")
        return f"<@{user_id}> Role <@&{role_id}> is restricted"

    return reply

async def execute_roles(guild_id):
    roles = await utility.getRoles(guild_id)

    joinableRoles = []
    for role in roles:
        if await utility.validateRole(guild_id, role, roles):
            joinableRoles.append(role["name"])

    joinableRoles = sorted(joinableRoles)
    return "```\n{}\n```".format("\n".join(joinableRoles))

async def execute_members(role_id, guild_id):
    url = f"{GUILD_URL}/{guild_id}/members"

    r = await utility.get([HTTP_200_OK], url, params = {"limit": 200})
    members = r.json()
    reply = ""

    for member in members:
        if role_id in member["roles"]:
            reply += member["user"]["username"] + "\n"
    
    return f"```\n{reply}```"

def execute_myroles(roles):
    reply = ""

    for role_id in roles:
        reply += f"<@&{role_id}>\n"
    
    return reply

def execute_optime(today, modifier):
    try:
        opday = today
        opday = opday.replace(hour = 18 + modifier, minute = 0, second = 0)
        if today > opday:
            opday = opday + timedelta(days = 1)

        if modifier == 0:
            modifierString = ""
        elif modifier > 0:
            modifierString = f" +{modifier}"
        else:
            modifierString = f" {modifier}"

        timeUntilOptime = opday - today
        return f"Optime{modifierString} starts in {timeUntilOptime}!"
    except ValueError:
        return "Optime modifier is too large"

async def execute_addrole(guild_id, name):
    roles = await utility.getRoles(guild_id)

    for role in roles:
        if role["name"].lower() == name.lower():
            role_id = role["id"]
            return f"<@&{role_id}> already exists"

    url = f"{GUILD_URL}/{guild_id}/roles"
    r = await utility.post([HTTP_200_OK], url, json = {"name": name, "mentionable": True})
    role_id = r.json()["id"]

    return f"<@&{role_id}> added"

async def execute_removerole(guild_id, role_id):
    if await utility.validateRoleById(guild_id, role_id):
        url = f"{GUILD_URL}/{guild_id}/roles/{role_id}"

        await utility.delete([HTTP_204_NO_CONTENT], url)
        return "Role deleted"
    else:
        return "Role is restricted"

async def handle_interaction(interact):
    if (interact.get("type") == InteractionType.APPLICATION_COMMAND):
        data = interact["data"]
        command = data["name"]
        
        try:
            options = data.get("options")
            member = interact["member"]
            user = member["user"]
            username = user["username"]
            guild_id = interact["guild_id"]

            logging.info(f"'{username}' executing '{command}'")
            
            if command == "ping":
                return utility.ImmediateReply("Pong!")

            elif command == "role":
                roles = member["roles"]
                role_id = options[0]["value"]
                user_id = user["id"]
                reply = await execute_role(roles, role_id, guild_id, user_id)

                return utility.ImmediateReply(reply, mentions = ["users"])

            elif command == "roles":
                reply = await execute_roles(guild_id)
                return utility.ImmediateReply(reply)

            elif command == "members":
                role_id = options[0]["value"]
                reply = await execute_members(role_id, guild_id)
                return utility.ImmediateReply(reply)

            elif command == "myroles":
                roles = member["roles"]
                reply = execute_myroles(roles)
                return utility.ImmediateReply(reply, ephemeral = True)

            elif command == "optime":
                if options is not None and len(options) > 0:
                    modifier = options[0]["value"]
                else:
                    modifier = 0

                reply = execute_optime(datetime.now(tz = timezone('Europe/London')), modifier)
                return utility.ImmediateReply(reply)

            elif command == "addrole":
                name = options[0]["value"]
                reply = await execute_addrole(guild_id, name)
                return utility.ImmediateReply(reply)

            elif command == "removerole":
                role_id = options[0]["value"]
                reply = await execute_removerole(guild_id, role_id)
                return utility.ImmediateReply(reply)

        except Exception as e:
            logging.error(f"Error executing '{command}':\n{str(e)})")
            raise HTTPException(status_code = HTTP_500_INTERNAL_SERVER_ERROR, detail = f"Error executing '{command}'")
        
        raise HTTPException(status_code = HTTP_501_NOT_IMPLEMENTED, detail = f"'{command}' is not a known command")
    else:
        raise HTTPException(status_code = HTTP_400_BAD_REQUEST, detail = "Not an application command")

def app():
    fast_app = FastAPI()

    @fast_app.post('/interaction/')
    async def interaction(request: Request):
        await utility.verify_request(request)

        interact = await request.json()
        if interact.get("type") == InteractionType.PING:
            return JSONResponse({'type': InteractionResponseType.PONG})

        return JSONResponse(await handle_interaction(interact))

    @fast_app.get('/abc/')
    def hello_world():
        return {"message", "Hello, World!"}

    return fast_app

app = app()

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port = 8000)
