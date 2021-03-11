import os
import logging
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

import google.cloud.logging
from flask import Flask, jsonify, abort, request
from dotenv import load_dotenv

load_dotenv()
PUBLIC_KEY = os.getenv("PUBLIC_KEY")
verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))

client = google.cloud.logging.Client()
client.get_default_handler()
client.setup_logging()

app = Flask(__name__)

def verifyRequest(request):
    try:
        signature = request.headers["X-Signature-Ed25519"]
        timestamp = request.headers["X-Signature-Timestamp"]
        body = request.data
        verify_key.verify(f"{timestamp}{body}".encode(), bytes.fromhex(signature))
        return True
    except BadSignatureError as e:
        logging.warning(f"Invalid request signature -> \n{str(e)}\n{signature}\n{timestamp}\n{bytes.fromhex(signature)}")
        abort(401, "invalid request signature")
        return False
    except Exception as e:
        errorText = "verifyRequest error -> \n{}".format(str(e))
        logging.warning(errorText)
        abort(401, errorText)
        return False


@app.route('/', methods=['POST'])
def ping():
    if (not verifyRequest(request)): return

    if request.json["type"] == 1:
        return jsonify({
            "type": 1
        })

@app.route('/abc/')
def hello_world():
    return "Hello, World!"

if __name__ == "__main__":
    app.run(debug = True, host='0.0.0.0')
