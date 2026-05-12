import multiprocessing
import os

# Port binding
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"

# Worker configuration
# We use 1 worker for free tier stability, uvicorn for FastAPI
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"

# Timeouts - Increased for long-running GEE tasks
timeout = 300
graceful_timeout = 60
keepalive = 5

# Shared memory for workers
worker_tmp_dir = "/dev/shm"

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"

# Preloading
preload_app = False

# Startup Logs
print(f"--- Gunicorn Starting ---")
print(f"Port: {bind}")
print(f"Workers: {workers}")
print(f"Timeout: {timeout}s")
print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
print(f"--------------------------")
