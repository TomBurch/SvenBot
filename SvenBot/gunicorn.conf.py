from main import gunicorn_logger

bind = '0.0.0.0:8000'
workers = 1
loglevel = "info"
worker_class = "uvicorn.workers.UvicornWorker"


# Server Hooks
def on_starting(server):
    gunicorn_logger.info(f"Starting Server {server}")


def post_request(worker, req, environ, resp):
    gunicorn_logger.info(f"Postreq: {resp}")