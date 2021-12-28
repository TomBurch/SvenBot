from main import app

bind = '0.0.0.0:8000'
workers = 1
loglevel = "info"
worker_class = "uvicorn.workers.UvicornWorker"


# Server Hooks
def on_starting(server):
    app.logger.info(f"Starting Server {server}")
