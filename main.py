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

        if data.get("name") == "ping":
            return jsonify({
                "type": InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
                "data": {
                    "content": "Pong!"
                }
            })

@app.route('/abc/')
def hello_world():
    return "Hello, World!"

if __name__ == "__main__":
    app.run(debug = True, host='0.0.0.0')
