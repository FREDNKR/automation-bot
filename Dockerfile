FROM python:3.11-slim

# Install system dependencies + Google Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    fonts-liberation \
    libnss3 \
    libgbm1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libu2f-udev \
    libvulkan1 \
    xdg-utils \
    --no-install-recommends \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render provides the PORT env var; gunicorn binds to it.
# --timeout 0 disables gunicorn's own worker timeout (see note below).
# --worker-class gthread --threads 4 means this worker can handle multiple
# things at once (e.g. answer a health-check ping) even while one thread is
# busy running the long Selenium automation loop. With the default sync
# worker, the whole process is blocked by that one busy thread and can't
# respond to anything else - including Render's own external health checks -
# which can cause Render to think the service is unresponsive and restart
# the whole container, wiping out the automation with zero error logged.
CMD gunicorn --bind 0.0.0.0:$PORT --timeout 0 --worker-class gthread --threads 4 --workers 1 --enable-stdio-inheritance app:app
