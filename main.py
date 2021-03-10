import os
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from flask import Flask, jsonify
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
verify_key = VerifyKey(bytes.fromhex(DISCORD_TOKEN))

app = Flask(__name__)

def verifyRequest(request):
    try:
        signature = request.headers["X-Signature-Ed25519"]
        timestamp = request.headers["X-Signature-Timestamp"]
        body = request.data
        return True
    except:
        abort(401, 'invalid request signature')
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
    if (not verifyRequest(request)): return
    
    return "Hello, World!"

if __name__ == "__main__":
    app.run(debug = True, host='0.0.0.0')
