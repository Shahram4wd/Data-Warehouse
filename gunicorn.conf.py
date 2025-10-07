import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
backlog = 2048

# Worker processes - Optimized for Render.com memory constraints
workers = 1  # Single worker for memory efficiency on Render.com
worker_class = "sync"
worker_connections = 100  # Reduced for memory efficiency
timeout = 120  # Reduced timeout to prevent memory buildup
keepalive = 2
max_requests = 500  # Restart workers more frequently to prevent memory leaks
max_requests_jitter = 50  # Smaller jitter range

# Memory management - Optimized for Render.com
worker_tmp_dir = "/dev/shm"
preload_app = True

# Force garbage collection and memory optimization
def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)
    # Force garbage collection on worker start
    import gc
    gc.collect()

def pre_request(worker, req):
    """Called before processing each request"""
    # Periodic garbage collection to prevent memory buildup
    import gc
    if hasattr(worker, '_request_count'):
        worker._request_count += 1
    else:
        worker._request_count = 1
    
    # Force GC every 50 requests to prevent memory accumulation
    if worker._request_count % 50 == 0:
        gc.collect()

def post_request(worker, req, environ, resp):
    """Called after processing each request"""
    # Additional cleanup for long-running requests
    import gc
    gc.collect()

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
