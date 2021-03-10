from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/', methods=['POST'])
def ping():
    if request.json["type"] == 1:
        return jsonify({
            "type": 1
        })

@app.route('/abc/')
def hello_world():
    return "Hello, World!"

if __name__ == "__main__":
    app.run(debug = True, host='0.0.0.0')
