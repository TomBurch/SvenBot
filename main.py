import os
import logging
import requests
from datetime import datetime, timedelta
from pytz import timezone

import google.cloud.logging
from flask import Flask, jsonify, abort, request
from flask_caching import Cache
from discord_interactions import verify_key_decorator, InteractionType, InteractionResponseType
import utility
from dotenv import load_dotenv

load_dotenv()
PUBLIC_KEY = os.getenv("PUBLIC_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")

cache = Cache(config = {'CACHE_TYPE': 'SimpleCache'})

app = Flask(__name__)
cache.init_app(app)

def execute_role(roles, role_id, guild_id, user_id):
    url = f"https://discord.com/api/v8/guilds/{guild_id}/members/{user_id}/roles/{role_id}"
    if role_id in roles:
        r = utility.req(requests.delete, [204, 403], url)
        reply = f"<@{user_id}> You've left <@&{role_id}>"
    else:
        r = utility.req(requests.put, [204, 403], url)
        reply = f"<@{user_id}> You've joined <@&{role_id}>"

    if r.status_code == 403:
        return f"<@{user_id}> Role <@&{role_id}> is restricted"

    return reply

def execute_roles(guild_id):
    url = f"https://discord.com/api/v8/guilds/{guild_id}/roles"
    r = utility.req(requests.get, [200], url)
    roles = r.json()

    botPosition = -1
    for role in roles:
        if role.get("tags", {}).get("bot_id") is not None:
            if role["tags"]["bot_id"] == CLIENT_ID:
                botPosition = role["position"]
    
    if botPosition == -1:
        return "ERROR: Unable to find bot's role"

    joinableRoles = []
    for role in roles:
        if role.get("tags", {}).get("bot_id") is None and role["position"] < botPosition:
            joinableRoles.append(role["name"])

    joinableRoles = sorted(joinableRoles)
    return "```\n{}\n```".format("\n".join(joinableRoles))

def execute_members(role_id, guild_id):
    url = f"https://discord.com/api/v8/guilds/{guild_id}/members"
    r = utility.req(requests.get, [200], url, params = {"limit": 200})
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

def execute_optime(today):
    opday = today
    opday = opday.replace(hour = 18, minute = 0, second = 0)
    if today > opday:
        opday = opday + timedelta(days = 1)

    return "Optime starts in {}!".format(opday - today)

def handle_interaction(request):
    if (request.json.get("type") == InteractionType.APPLICATION_COMMAND):
        data = request.json["data"]
        command = data["name"]
        
        try:
            member = request.json["member"]
            user = member["user"]
            username = user["username"]
            guild_id = request.json["guild_id"]

            logging.info(f"'{username}' executing '{command}'")
            
            if command == "ping":
                return utility.ImmediateReply("Pong!")

            elif command == "role":
                roles = member["roles"]
                role_id = data["options"][0]["value"]
                user_id = user["id"]
                reply = execute_role(roles, role_id, guild_id, user_id)

                return utility.ImmediateReply(reply, mentions = ["users"])

            elif command == "roles":
                reply = execute_roles(guild_id)
                return utility.ImmediateReply(reply, mentions = [])

            elif command == "members":
                role_id = data["options"][0]["value"]
                reply = execute_members(role_id, guild_id)
                return utility.ImmediateReply(reply, mentions = [])

            elif command == "myroles":
                roles = member["roles"]
                reply = execute_myroles(roles)
                return utility.ImmediateReply(reply, mentions = [], ephemeral = True)

            elif command == "optime":
                reply = execute_optime(datetime.now(tz = timezone('Europe/London')))
                return utility.ImmediateReply(reply)

        except Exception as e:
            logging.error(f"Error executing '{command}':\n{str(e)})")
            abort(404, f"Error executing '{command}'")
        
        abort(404, f"'{command}' is not a known command")
    else:
        abort(404, "Not an application command")

@app.route('/interaction/', methods=['POST'])
@verify_key_decorator(PUBLIC_KEY)
def interaction():
    return jsonify(handle_interaction(request))

@app.route('/abc/')
def hello_world():
    return "Hello, World!"

if __name__ == "__main__":
    client = google.cloud.logging.Client()
    client.get_default_handler()
    client.setup_logging()

    app.run(debug = True, host='0.0.0.0')
