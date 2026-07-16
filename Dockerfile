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
# --timeout 0 disables gunicorn's worker timeout entirely. This app runs a
# long background automation thread inside the same worker process - if that
# thread's blocking Selenium/network calls ever hold Python's GIL long enough,
# gunicorn's internal health-check can't get through, and with a timeout set
# it will silently kill and restart the ENTIRE process (wiping out the
# automation with zero error logged). Disabling it removes that risk.
CMD gunicorn --bind 0.0.0.0:$PORT --timeout 0 --enable-stdio-inheritance app:app