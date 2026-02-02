# AI System - Dockerfile
# Single-container image for complete system execution
# Includes: Programmer, Scheduler, Telegram interface, Gmail reader

# Base image: Python 3.10 slim (Debian-based, minimal footprint)
FROM python:3.10-slim

# Install minimal system dependencies
# - git: Required for Aider and version control operations
# - curl: Useful for health checks and debugging
# - ca-certificates: SSL/TLS for API calls (Telegram, Gmail)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        curl \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
# Note: Ensure .dockerignore excludes __pycache__, *.pyc, .git, etc.
COPY . /app

# Install Python dependencies
# --no-cache-dir: Reduce image size by not caching pip packages
RUN pip install --no-cache-dir -r requirements.txt

# Declare volumes for ephemeral/external data
# These should be mounted at runtime, NOT baked into the image
VOLUME ["/app/node_programmer/workspaces"]
VOLUME ["/app/node_programmer/sandbox"]
VOLUME ["/app/audits"]
VOLUME ["/app/secrets"]

# Create non-root user for security
# Running as root inside containers is a security risk
RUN useradd -m -u 1000 aiuser && \
    chown -R aiuser:aiuser /app

# Switch to non-root user
USER aiuser

# Set Python to run in unbuffered mode (better for logs)
ENV PYTHONUNBUFFERED=1

# Default command: Interactive shell
# Users should explicitly run:
#   - python node_interface/telegram_bot.py  (for Telegram bot)
#   - python -c "from node_scheduler import Scheduler; Scheduler().run()"  (for scheduler)
#   - python -m pytest  (for tests)
# This prevents accidental execution on container start
CMD ["/bin/bash"]
