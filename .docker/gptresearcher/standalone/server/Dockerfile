# Stage 1: Browser and build tools installation
FROM python:3.12-slim-bookworm AS install-browser

# 1. Installiere Tools
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    gnupg \
    unzip \
    jq \
    ca-certificates \
    --no-install-recommends

# 2. Chrome installieren
RUN wget -q -O google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y ./google-chrome.deb \
    && rm google-chrome.deb

# 3. Chromedriver installieren
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}') \
    && DRIVER_URL=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json" | \
    jq -r --arg VER "$CHROME_VERSION" '.versions[] | select(.version==$VER) | .downloads.chromedriver[] | select(.platform=="linux64") | .url') \
    && if [ -z "$DRIVER_URL" ]; then \
    DRIVER_URL=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json" | \
    jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform=="linux64") | .url'); \
    fi \
    && wget -q -O chromedriver.zip "$DRIVER_URL" \
    && unzip chromedriver.zip \
    && mv chromedriver-linux64/chromedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf chromedriver.zip chromedriver-linux64

# Path Check
RUN google-chrome --version && chromedriver --version
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Stage 2: Python dependencies
FROM install-browser AS gpt-researcher-install

ENV PIP_ROOT_USER_ACTION=ignore
WORKDIR /usr/src/app

# Repo klonen
RUN git clone https://github.com/assafelovic/gpt-researcher.git ./

# --- CODE FIXES FÜR DOCKER ---

# 1. Headless aktivieren (Verhindert GUI-Fehler)
RUN sed -i 's/self.headless = False/self.headless = True/' /usr/src/app/gpt_researcher/scraper/browser/browser.py

# 2. CRASH FIX: Remote-Debugging-Port entfernen (Verhindert "disconnected"-Fehler)
RUN sed -i '/--remote-debugging-port=9222/d' /usr/src/app/gpt_researcher/scraper/browser/browser.py

# 3. STABILITÄT: GPU deaktivieren (Verhindert Renderer-Crashes bei komplexen Seiten)
# Wir fügen --disable-gpu und --window-size nach der Zeile "--no-sandbox" ein.
RUN sed -i '/options.add_argument("--no-sandbox")/a \        options.add_argument("--disable-gpu")\n        options.add_argument("--window-size=1920,1080")' /usr/src/app/gpt_researcher/scraper/browser/browser.py

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

RUN useradd -ms /bin/bash gpt-researcher && \
    chown -R gpt-researcher:gpt-researcher /usr/src/app && \
    mkdir -p /usr/src/app/outputs && \
    chown -R gpt-researcher:gpt-researcher /usr/src/app/outputs && \
    chmod 777 /usr/src/app/outputs

USER gpt-researcher
WORKDIR /usr/src/app
COPY --chown=gpt-researcher:gpt-researcher ./ ./

CMD uvicorn main:app --host ${HOST} --port ${PORT} --workers ${WORKERS}