bind = "127.0.0.1:8000"  # IP and port to bind to
# workers = 3  # Number of worker processes
# worker_class = "sync"  # Type of workers to use (e.g., "sync", "gevent")
timeout = 3600  # Workers silent for more than this many seconds are killed and restarted
# loglevel = "info"  # The granularity of log output
# errorlog = "-"  # Error log - "-" means log to stderr
# accesslog = "-"  # Access log - "-" means log to stderr
# keepalive =   # Keepalive duration in seconds

# # Security settings
# limit_request_line = 4094  # Maximum size of HTTP request line in bytes
# limit_request_fields = 20  # Maximum number of headers in a request

# # Performance tuning
# max_requests = 1000  # Restart each worker after it has handled this many requests
# max_requests_jitter = 50  # The maximum jitter to add to the max_requests setting

# SSL configuration (if using SSL)
# certfile = "/path/to/certfile"
# keyfile = "/path/to/keyfile"