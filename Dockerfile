# syntax=docker/dockerfile:1
# Keep this syntax directive! It's used to enable Docker BuildKit

# Use a specific Python 3.11 slim image as the base
# FROM python:3.11.3-slim
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    unzip \
    xvfb \
    xauth \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libxss1 \
    libasound2 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libdrm2 \
    libgbm1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxinerama1 \
    libxcursor1 \
    libxi6 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Set work directory
WORKDIR /app

# Copy project files
COPY . /app/

# Install Python dependencies (as root, includes playwright CLI for next step)
RUN uv sync --frozen --no-install-project --no-editable

# Install the project itself with memory extras
RUN uv pip install /app[memory]

# Explicitly install playwright if not a direct project dependency
# RUN pip install playwright

# Install Playwright and browsers with system dependencies (as root)
ENV BROWSER_USE_LOGGING_LEVEL=info
ENV ANONYMIZED_TELEMETRY=false
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV CHROME_PATH=/ms-playwright/chromium-*/chrome-linux/chrome
ENV CHROME_PERSISTENT_SESSION=true
ENV DISPLAY=:99
ENV RESOLUTION=1920x1080x24
ENV RESOLUTION_WIDTH=1920
ENV RESOLUTION_HEIGHT=1080

RUN /app/.venv/bin/playwright install --with-deps chromium

# Change ownership to the non-root user
RUN chown -R appuser:appgroup /app
RUN mkdir -p ${PLAYWRIGHT_BROWSERS_PATH} && chown -R appuser:appgroup ${PLAYWRIGHT_BROWSERS_PATH}

# Switch to non-root user
USER appuser

# Add user's local bin directory to PATH (useful for appuser's own tools)
ENV PATH="/home/appuser/.local/bin:/app/.venv/bin:${PATH}"

# Set the cache directory for uv
RUN mkdir -p /app/.cache/uv
ENV UV_CACHE_DIR="/app/.cache/uv"

# Set the directory for mem0
RUN mkdir -p /app/.mem0
ENV MEM0_DIR="/app/.mem0"

# Define health check (example: adjust as needed)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#   CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8881

# Define default command
# CMD ["browser-use"]
# CMD ["xvfb-run", "-a", "--server-args='-screen 0 ${RESOLUTION_WIDTH}x${RESOLUTION_HEIGHT}x24'", "uv", "run", "/app/examples/models/api_server.py"]
CMD ["xvfb-run", "-a", "--server-args=-screen 0 ${RESOLUTION_WIDTH}x${RESOLUTION_HEIGHT}x24", "uv", "run", "/app/examples/models/gemini.py"]
