# Stage 1: Browser and build tools installation
# Python 3.12+ required for LangChain v1
FROM python:3.12-slim-bookworm AS install-browser

# Install Chromium, Chromedriver, Firefox, Geckodriver, and build tools in one layer
RUN apt-get update \
    && apt-get install -y gnupg wget ca-certificates --no-install-recommends \
    && ARCH=$(dpkg --print-architecture) \
    && wget -qO - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=${ARCH}] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y chromium chromium-driver \
    && chromium --version && chromedriver --version \
    && apt-get install -y --no-install-recommends firefox-esr build-essential \
    && GECKO_ARCH=$(case ${ARCH} in amd64) echo "linux64" ;; arm64) echo "linux-aarch64" ;; *) echo "linux64" ;; esac) \
    && wget https://github.com/mozilla/geckodriver/releases/download/v0.36.0/geckodriver-v0.36.0-${GECKO_ARCH}.tar.gz \
    && tar -xvzf geckodriver-v0.36.0-${GECKO_ARCH}.tar.gz \
    && chmod +x geckodriver \
    && mv geckodriver /usr/local/bin/ \
    && rm geckodriver-v0.36.0-${GECKO_ARCH}.tar.gz \
    && rm -rf /var/lib/apt/lists/*  # Clean up apt lists to reduce image size

# install selenium
# Installiere benötigte Systempakete und fehlende Bibliotheken für Chromedriver
RUN apt-get update && \
    apt-get install -y \
    git \
    wget \
    unzip \
    xvfb \
    cron \
    gnupg2 \
    curl \
    jq \
    nano \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libxshmfence1 \
    libxrandr2 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libxcomposite1 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libatspi2.0-0 \
    libxdamage1 \
    libgbm1 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Definiere Umgebungsvariablen für die Download-URLs
ENV JSON_URL="https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"

# Lade und installiere Google Chrome und ChromeDriver
RUN set -ex; \
    # Hole Download-URLs für Chrome und ChromeDriver aus dem JSON
    CHROME_URL=$(curl -s $JSON_URL | jq -r '.channels.Stable.downloads.chrome[] | select(.platform=="linux64").url'); \
    CHROMEDRIVER_URL=$(curl -s $JSON_URL | jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform=="linux64").url'); \
    # Lade Chrome und ChromeDriver herunter
    wget -q $CHROME_URL -O chrome-linux64.zip; \
    wget -q $CHROMEDRIVER_URL -O chromedriver-linux64.zip; \
    # Entpacke und installiere Chrome und ChromeDriver
    unzip chrome-linux64.zip -d /opt/chrome; \
    unzip chromedriver-linux64.zip -d /opt/chromedriver; \
    # Erstelle symbolische Links
    find /opt/chrome -name 'chrome' -type f -exec ln -sf {} /usr/bin/google-chrome \;; \
    find /opt/chromedriver -name 'chromedriver' -type f -exec ln -sf {} /usr/local/bin/chromedriver \;; \
    chmod +x /usr/local/bin/chromedriver

# Füge eine neue RUN-Anweisung hinzu, um die Abhängigkeiten von Chromedriver zu überprüfen
RUN ldd /usr/local/bin/chromedriver || true
RUN ldd /usr/bin/google-chrome || true

# Add to path
ENV PATH="/usr/local/bin/chromedriver:/usr/bin/google-chrome:${PATH}"

# Stage 2: Python dependencies installation
FROM install-browser AS gpt-researcher-install

ENV PIP_ROOT_USER_ACTION=ignore
WORKDIR /usr/src/app

# install git and clone repo
RUN git clone https://github.com/assafelovic/gpt-researcher.git ./

RUN pip install --upgrade pip && \
    pip install selenium && \
    pip install --no-cache-dir -r requirements.txt --upgrade --prefer-binary && \
    pip install --no-cache-dir -r multi_agents/requirements.txt --upgrade --prefer-binary

# Stage 3: Final stage with non-root user and app
FROM gpt-researcher-install AS gpt-researcher

# Basic server configuration
ARG HOST=0.0.0.0
ENV HOST=${HOST}
ARG PORT=8000
ENV PORT=${PORT}
EXPOSE ${PORT}

# Uvicorn parameters used in CMD
ARG WORKERS=1
ENV WORKERS=${WORKERS}

# Create a non-root user for security
# NOTE: Don't use this if you are relying on `_check_pkg` to pip install packages dynamically.
RUN useradd -ms /bin/bash gpt-researcher && \
    chown -R gpt-researcher:gpt-researcher /usr/src/app && \
    # Add these lines to create and set permissions for outputs directory
    mkdir -p /usr/src/app/outputs && \
    chown -R gpt-researcher:gpt-researcher /usr/src/app/outputs && \
    chmod 777 /usr/src/app/outputs
USER gpt-researcher
WORKDIR /usr/src/app

# Copy the rest of the application files with proper ownership
COPY --chown=gpt-researcher:gpt-researcher ./ ./
CMD uvicorn main:app --host ${HOST} --port ${PORT} --workers ${WORKERS}