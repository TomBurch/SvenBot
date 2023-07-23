bind = "0.0.0.0"
workers = 1
loglevel = "info"
worker_class = "uvicorn.workers.UvicornWorker"
accesslog = "./access.txt"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
