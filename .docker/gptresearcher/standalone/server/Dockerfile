# Stage 1: Browser and build tools installation
FROM python:3.12-slim-bookworm AS install-browser

# Installiere grundlegende Tools
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip \
    jq \
    ca-certificates \
    --no-install-recommends

# --- INSTALLATION GOOGLE CHROME (STABLE) ---
# Wir nutzen das offizielle .deb Paket, damit apt alle fehlenden Libs (libasound, libnss, etc.) automatisch zieht.
RUN wget -q -O google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y ./google-chrome.deb \
    && rm google-chrome.deb

# --- INSTALLATION CHROMEDRIVER ---
# Ermittle die installierte Chrome-Version und lade den exakt passenden Treiber
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}') \
    && echo "Installed Chrome Version: $CHROME_VERSION" \
    # Hole die URL für den passenden Chromedriver von der offiziellen JSON-API
    && DRIVER_URL=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json" | \
    jq -r --arg VER "$CHROME_VERSION" '.versions[] | select(.version==$VER) | .downloads.chromedriver[] | select(.platform=="linux64") | .url') \
    # Fallback: Falls exakte Version nicht im JSON ist (passiert bei ganz neuen Updates), nimm die Latest Version URL
    && if [ -z "$DRIVER_URL" ]; then \
    echo "Exakte Version nicht gefunden, suche Major-Version..."; \
    MAJOR_VER=$(echo $CHROME_VERSION | cut -d. -f1); \
    DRIVER_URL=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json" | \
    jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform=="linux64") | .url'); \
    fi \
    && echo "Downloading Chromedriver from: $DRIVER_URL" \
    && wget -q -O chromedriver.zip "$DRIVER_URL" \
    && unzip chromedriver.zip \
    && mv chromedriver-linux64/chromedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf chromedriver.zip chromedriver-linux64

# Firefox/Gecko (optional, falls benötigt, sonst entfernen um Image klein zu halten)
RUN apt-get install -y firefox-esr \
    && wget https://github.com/mozilla/geckodriver/releases/download/v0.36.0/geckodriver-v0.36.0-linux64.tar.gz \
    && tar -xvzf geckodriver-v0.36.0-linux64.tar.gz \
    && mv geckodriver /usr/local/bin/ \
    && rm geckodriver-v0.36.0-linux64.tar.gz

# Aufräumen
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Stage 2: Python dependencies
FROM install-browser AS gpt-researcher-install

ENV PIP_ROOT_USER_ACTION=ignore
WORKDIR /usr/src/app

RUN git clone https://github.com/assafelovic/gpt-researcher.git ./

RUN pip install --upgrade pip && \
    pip install selenium && \
    pip install --no-cache-dir -r requirements.txt --upgrade --prefer-binary && \
    pip install --no-cache-dir -r multi_agents/requirements.txt --upgrade --prefer-binary

# Stage 3: Final Stage
FROM gpt-researcher-install AS gpt-researcher

ARG HOST=0.0.0.0
ENV HOST=${HOST}
ARG PORT=8000
ENV PORT=${PORT}
EXPOSE ${PORT}
ARG WORKERS=1
ENV WORKERS=${WORKERS}

# User Setup
RUN useradd -ms /bin/bash gpt-researcher && \
    chown -R gpt-researcher:gpt-researcher /usr/src/app && \
    mkdir -p /usr/src/app/outputs && \
    chown -R gpt-researcher:gpt-researcher /usr/src/app/outputs && \
    chmod 777 /usr/src/app/outputs

USER gpt-researcher
WORKDIR /usr/src/app
COPY --chown=gpt-researcher:gpt-researcher ./ ./

CMD uvicorn main:app --host ${HOST} --port ${PORT} --workers ${WORKERS}