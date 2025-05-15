# syntax=docker/dockerfile:1
# Keep this syntax directive! It's used to enable Docker BuildKit

########################################
## Stage 1: Builder
########################################
# FROM ghcr.io/astral-sh/uv:python3.12-alpine AS builder
# FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder
FROM ghcr.io/astral-sh/uv:python3.11-bookworm AS builder

# Set environment variables for build stage
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    TZ=Asia/Taipei 
    # PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install build-time system dependencies, clean up apt cache
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     git \
#     curl \
#     && rm -rf /var/lib/apt/lists/*

# Install noVNC
# RUN git clone --depth 1 https://github.com/novnc/noVNC.git /opt/novnc && \
#     git clone --depth 1 https://github.com/novnc/websockify.git /opt/novnc/utils/websockify && \
#     ln -sf /opt/novnc/vnc.html /opt/novnc/index.html

# Set work directory
WORKDIR /app

# 複製並安裝 Python 依賴（不安裝專案程式碼）
# COPY pyproject.toml uv.lock ./
# RUN python3 -m venv .venv && \
#     .venv/bin/pip install --no-cache-dir --upgrade pip && \
#     .venv/bin/pip install --no-cache-dir uv && \
#     .venv/bin/uv sync --frozen --no-install-project

# Copy project files
# COPY . .

# Install the project itself with memory extras
# Install playwright if not a direct project dependency
# Install Playwright browser binaries (without system dependencies at this stage)
# RUN .venv/bin/uv pip install /app[memory] playwright && \
#     .venv/bin/playwright install chromium


########################################
## Stage 2: Final
########################################
# FROM python:3.11-slim AS final

# Set environment variables
# ENV PYTHONDONTWRITEBYTECODE=1 \
#     PYTHONUNBUFFERED=1 \
#     UV_LINK_MODE=copy \
#     TZ=Asia/Taipei \
#     PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
#     ANONYMIZED_TELEMETRY=false \
#     BROWSER_USE_LOGGING_LEVEL=info \
#     CHROME_PATH=/ms-playwright/chromium-*/chrome-linux/chrome \
#     CHROME_PERSISTENT_SESSION=true \
#     DISPLAY=:99 \
#     RESOLUTION=1920x1080x24 \
#     RESOLUTION_WIDTH=1920 \
#     RESOLUTION_HEIGHT=1080 \
#     VNC_PASSWORD=vncpassword \
#     UV_CACHE_DIR="/app/.cache/uv" \
#     MEM0_DIR="/app/.mem0" \
#     PATH="/home/appuser/.local/bin:/app/.venv/bin:${PATH}"

# Install runtime system dependencies
    # net-tools \
    # procps \
    # libcups2 \
    # libxss1 \
    # libdbus-1-3 \
    # fonts-dejavu-extra \
    # python3-numpy \

# RUN apt-get update && apt-get install -y --no-install-recommends \
#     netcat-traditional \
#     xvfb \
#     xauth \
#     x11vnc \
#     tigervnc-tools \
#     libnss3 \
#     libnspr4 \
#     libatk1.0-0 \
#     libatk-bridge2.0-0 \
#     libgtk-3-0 \
#     libasound2 \
#     libx11-xcb1 \
#     libxcb-dri3-0 \
#     libdrm2 \
#     libgbm1 \
#     libxcomposite1 \
#     libxdamage1 \
#     libxfixes3 \
#     libxrandr2 \
#     libfontconfig1 \
#     fontconfig \
#     fonts-liberation \
#     fonts-dejavu \
#     fonts-dejavu-core \
#     supervisor \
#     libxinerama1 \
#     libxcursor1 \
#     libxi6 \
#     libgl1-mesa-glx \
#     && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*

# Create a non-root user
# RUN addgroup --system appgroup && \
#     adduser --system --ingroup appgroup appuser

# Set work directory
# WORKDIR /app

# 複製 Builder 產物：應用程式、venv、noVNC、Playwright 瀏覽器
# COPY --from=builder /app /app
# COPY --from=builder /opt/novnc /opt/novnc
# COPY --from=builder ${PLAYWRIGHT_BROWSERS_PATH} ${PLAYWRIGHT_BROWSERS_PATH}

# Install Playwright browser system dependencies for the copied browsers
# RUN .venv/bin/playwright install-deps chromium

# Set up supervisor configuration
# COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
# RUN mkdir -p /var/log/supervisor

# Switch to non-root user
# USER appuser 

# Change ownership to the non-root user for relevant directories
# RUN mkdir -p /app/.cache/uv && \
#     mkdir -p /app/.mem0 && \
#     mkdir -p ${PLAYWRIGHT_BROWSERS_PATH}
# RUN chown -R appuser:appgroup /app && \
#     chown -R appuser:appgroup ${PLAYWRIGHT_BROWSERS_PATH}

# EXPOSE ports
# EXPOSE 8881 6080 

# CMD ["browser-use"]
# Define default command (supervisord will run as root)
# CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
