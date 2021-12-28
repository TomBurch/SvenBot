from main import gunicorn_logger

bind = '0.0.0.0:8000'
workers = 1
loglevel = "info"
worker_class = "uvicorn.workers.UvicornWorker"
accesslog = "./access.txt"


# Server Hooks
def on_starting(server):
    gunicorn_logger.info(f"Starting Server {server}")


def pre_request(worker, req):
    worker.log.debug("%s %s" % (req.method, req.path))
    gunicorn_logger.info("%s %s" % (req.method, req.path))


def post_request(worker, req, environ, resp):
    gunicorn_logger.info(f"Postreq: {resp}")