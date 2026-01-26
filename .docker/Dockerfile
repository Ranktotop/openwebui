# ------------------------------
# Morphik UI Dockerfile (Production Build, ENV-getrieben)
# ------------------------------

FROM node:20-alpine AS builder

WORKDIR /app

# Git & bash für Repo klonen
RUN apk add --no-cache git bash curl

# Morphik Core Repo klonen
RUN git clone --depth 1 https://github.com/morphik-org/morphik-core.git .

# Ins UI-Verzeichnis wechseln
WORKDIR /app/ee/ui-component

# Node Dependencies installieren
RUN npm install --legacy-peer-deps

# Production Build erzeugen
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build --no-lint

# ------------------------------
# Final Image
# ------------------------------
FROM node:20-alpine

WORKDIR /app

# Copy Production Build
COPY --from=builder /app/ee/ui-component/.next ./.next
COPY --from=builder /app/ee/ui-component/public ./public
COPY --from=builder /app/ee/ui-component/package.json ./package.json
COPY --from=builder /app/ee/ui-component/node_modules ./node_modules

# Dev-Port freigeben
EXPOSE 3000

# ENV für Morphik API aus Compose
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl --fail http://localhost:3000 || exit 1

# Production-Server starten
CMD ["npm", "run", "start", "--", "-H", "0.0.0.0"]
