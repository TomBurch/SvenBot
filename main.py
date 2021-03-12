import os
import logging

import google.cloud.logging
from flask import Flask, jsonify, abort, request
from discord_interactions import verify_key_decorator, InteractionType, InteractionResponseType
from dotenv import load_dotenv

load_dotenv()
PUBLIC_KEY = os.getenv("PUBLIC_KEY")

client = google.cloud.logging.Client()
client.get_default_handler()
client.setup_logging()

app = Flask(__name__)

@app.route('/interaction/', methods=['POST'])
@verify_key_decorator(PUBLIC_KEY)
def interaction():
    if (request.json.get("type") == InteractionType.APPLICATION_COMMAND):
        data = request.json.get("data")
        command = data.get("name")

        try:
            logging.debug(f"Executing '{command}'")
            
            if command == "ping":
                return jsonify({
                    "type": InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
                    "data": {
                        "content": "Pong!"
                    }
                })
            elif command == "role":
                logger.debug(str(data.get("options")))
                return jsonify({
                    "type": InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
                    "data": {
                        "content": f"Executing role"
                    }
                })
        except Exception as e:
            logging.error(f"Error executing '{command}':\n{str(e)})")
            abort(404, f"Error executing '{command}'")
        
        abort(404, f"'{command}' is not a known command")
    else:
        abort(404, "Not an application command")

@app.route('/abc/')
def hello_world():
    return "Hello, World!"

if __name__ == "__main__":
    app.run(debug = True, host='0.0.0.0')
