import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
backlog = 2048

# Worker processes - Reduced for better memory management
workers = min(2, multiprocessing.cpu_count())  # Reduced from 4
worker_class = "sync"
worker_connections = 1000
timeout = 300  # Increased timeout for long-running sync operations
keepalive = 5
max_requests = 2000  # Increased before worker restart
max_requests_jitter = 200

# Memory management
worker_tmp_dir = "/dev/shm"
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "data_warehouse"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
keyfile = None
certfile = None

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def worker_exit(server, worker):
    """Log worker exits with reason"""
    # Worker object may not have exitcode attribute, handle gracefully
    try:
        exit_code = getattr(worker, 'exitcode', 'unknown')
        server.log.info("Worker exiting (pid: %s) - Exit code: %s", worker.pid, exit_code)
    except AttributeError:
        server.log.info("Worker exiting (pid: %s)", worker.pid)

def on_exit(server):
    """Log server shutdown"""
    server.log.info("Shutting down: Master")
