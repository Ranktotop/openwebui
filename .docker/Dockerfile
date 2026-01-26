# ------------------------------
# Morphik UI Dockerfile (UI-only, Dev Mode)
# ------------------------------

FROM node:20-alpine

# Arbeitsverzeichnis
WORKDIR /app

# Git installieren, um repo zu klonen
RUN apk add --no-cache git bash

# Morphik Core Repo klonen
RUN git clone --depth 1 https://github.com/morphik-org/morphik-core.git .

# Ins UI-Verzeichnis wechseln
WORKDIR /app/ee/ui-component

# Node Dependencies installieren
RUN npm install

# Dev-Port freigeben
EXPOSE 3000

# API URL auf Morphik Server setzen
ENV NEXT_PUBLIC_API_URL=http://morphik_server:8000
ENV WATCHPACK_POLLING=true

# Dev-Server starten
CMD ["npm", "run", "dev"]
