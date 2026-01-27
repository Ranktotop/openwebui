# ------------------------------
# Morphik UI Dockerfile (Production Build)
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

# ESLint beim Build deaktivieren
RUN echo 'module.exports = { eslint: { ignoreDuringBuilds: true } }' > next.config.js

# Production Build mit relativer URL für nginx
ENV NEXT_PUBLIC_API_URL=/api
RUN npm run build

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

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl --fail http://localhost:3000 || exit 1

CMD ["npm", "run", "start", "--", "-H", "0.0.0.0"]