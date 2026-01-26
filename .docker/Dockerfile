# ------------------------------
# Morphik UI Dockerfile (UI-only, Dev Mode)
# ------------------------------

FROM node:20-alpine

WORKDIR /app

# Git & bash für repo klonen
RUN apk add --no-cache git bash curl

# Morphik Core Repo klonen
RUN git clone --depth 1 https://github.com/morphik-org/morphik-core.git .

# Ins UI-Verzeichnis wechseln
WORKDIR /app/ee/ui-component

# Node Dependencies installieren
RUN npm install

# Dev-Port freigeben
EXPOSE 3000

# ENV für Watchpack Polling
ENV WATCHPACK_POLLING=true

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl --fail http://localhost:3000/ || exit 1

# Dev-Server starten (bindet an 0.0.0.0)
CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0"]
