# Stage 1: Browser and build tools installation
FROM python:3.12-slim-bookworm AS install-browser

# 1. Installiere Tools (WICHTIG: git muss hier dabei sein)
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    gnupg \
    unzip \
    jq \
    ca-certificates \
    --no-install-recommends

# 2. INSTALLATION GOOGLE CHROME (STABLE)
# Das .deb Paket installiert Chrome automatisch nach /usr/bin/google-chrome (bereits im PATH)
RUN wget -q -O google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y ./google-chrome.deb \
    && rm google-chrome.deb

# 3. INSTALLATION CHROMEDRIVER
# Wir verschieben den Treiber nach /usr/local/bin/, was ebenfalls Standard-PATH ist.
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}') \
    && echo "Installed Chrome Version: $CHROME_VERSION" \
    && DRIVER_URL=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json" | \
    jq -r --arg VER "$CHROME_VERSION" '.versions[] | select(.version==$VER) | .downloads.chromedriver[] | select(.platform=="linux64") | .url') \
    # Fallback logik falls exakte Version nicht im JSON
    && if [ -z "$DRIVER_URL" ]; then \
    echo "Exakte Version nicht gefunden, nutze Latest Stable..."; \
    DRIVER_URL=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json" | \
    jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform=="linux64") | .url'); \
    fi \
    && echo "Downloading Chromedriver from: $DRIVER_URL" \
    && wget -q -O chromedriver.zip "$DRIVER_URL" \
    && unzip chromedriver.zip \
    && mv chromedriver-linux64/chromedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf chromedriver.zip chromedriver-linux64

# 4. PATH TEST (Zur Sicherheit)
# Dieser Befehl schlägt fehl, wenn Chrome oder Driver nicht im Path sind -> Build bricht ab.
RUN google-chrome --version && chromedriver --version

# Aufräumen
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Stage 2: Python dependencies
FROM install-browser AS gpt-researcher-install

ENV PIP_ROOT_USER_ACTION=ignore
WORKDIR /usr/src/app

# Jetzt funktioniert git clone, da git in Stage 1 installiert wurde
RUN git clone https://github.com/assafelovic/gpt-researcher.git ./

# --- FIX: FORCE HEADLESS & DOCKER OPTIONS ---
# Wir nutzen sed, um die Zeilen VOR der Treiber-Initialisierung einzufügen.
# WICHTIG: Die 16 Leerzeichen am Anfang sind für die Python-Einrückung notwendig!
RUN sed -i "/self.driver = webdriver.Chrome(options=options)/i \\
    options.add_argument('--headless')\\n\
    options.add_argument('--no-sandbox')\\n\
    options.add_argument('--disable-dev-shm-usage')" \
    /usr/src/app/gpt_researcher/scraper/browser/browser.py

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