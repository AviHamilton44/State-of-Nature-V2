import os

# Gunicorn configuration for Render
bind = "0.0.0.0:" + os.environ.get("PORT", "10000")
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 300
keepalive = 5
loglevel = "info"
capture_output = True
enable_stdio_inheritance = True
