import os
import logging
import requests

import google.cloud.logging
from flask import Flask, jsonify, abort, request
from flask_caching import Cache
from discord_interactions import verify_key_decorator, InteractionType, InteractionResponseType
from dotenv import load_dotenv

load_dotenv()
PUBLIC_KEY = os.getenv("PUBLIC_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")

headers = {
    "Authorization": f"Bot {BOT_TOKEN}"
}

cache = Cache(config = {'CACHE_TYPE': 'SimpleCache'})

app = Flask(__name__)
cache.init_app(app)

def handle_interaction(request):
    if (request.json.get("type") == InteractionType.APPLICATION_COMMAND):
        data = request.json.get("data")
        member = request.json.get("member")
        command = data.get("name")
        
        try:
            logging.info(f"Executing '{command}'")
            
            if command == "ping":
                return {
                    "type": InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
                    "data": {
                        "content": "Pong!"
                    }
                }
            elif command == "role":
                role_id = data.get("options")[0].get("value")
                guild_id = request.json.get("guild_id")
                user_id = member.get("user").get("id")

                url = f"https://discord.com/api/v8/guilds/{guild_id}/members/{user_id}/roles/{role_id}"
                if role_id in member.get("roles"):
                    r = requests.delete(url, headers = headers)
                    response = f"You have left <&{role_id}>"
                else:
                    r = requests.put(url, headers = headers)
                    response = f"You have joined <&{role_id}>"

                return {
                    "type": InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
                    "data": {
                        "content": response
                    }
                }
                
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
