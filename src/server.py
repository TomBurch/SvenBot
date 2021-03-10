from flask import Flask
from waitress import serve
app = Flask(__name__)

@app.route('/abc/')
def hello_world():
    return "Hello, World!"

if __name__ == "__main__":
    app.run(debug = True, host='0.0.0.0')