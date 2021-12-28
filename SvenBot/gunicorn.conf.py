from main import gunicorn_logger

bind = '0.0.0.0'
workers = 1
loglevel = "info"
worker_class = "uvicorn.workers.UvicornWorker"
accesslog = "./access.txt"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'


# Server Hooks
def on_starting(server):
    gunicorn_logger.info(f"Starting Server {server}")


def pre_request(worker, req):
    worker.log.debug("%s %s" % (req.method, req.path))
    gunicorn_logger.info("%s %s" % (req.method, req.path))


def post_request(worker, req, environ, resp):
    gunicorn_logger.info(f"Postreq: {resp}")