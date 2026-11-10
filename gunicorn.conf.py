"""
Gunicorn configuration for production deployment (Render / container / Linux VM).
"""
import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
backlog = 2048

# Worker processes tuned for high concurrency and load balancing (handling 4,000+ campus members)
workers = int(os.environ.get("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "gthread")
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
worker_connections = int(os.environ.get("GUNICORN_WORKER_CONNECTIONS", "1000"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "60"))
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "campusconnect"

# Preload app code before worker processes are forked
preload_app = True
