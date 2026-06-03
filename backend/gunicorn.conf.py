# Gunicorn configuration file
# Automatically loaded by Gunicorn at startup

# Timeout duration in seconds (increased to 120s to tolerate CPU cold-starts and ML inference time)
timeout = 120

# Number of worker processes (pinned to 1 to prevent memory overload on 512MB RAM free tier)
workers = 1

# Number of threads per worker
threads = 1

# Disable app preloading to prevent PyTorch fork deadlocks in child worker processes
preload_app = False

# Use simple sync workers for CPU bounds
worker_class = 'sync'
