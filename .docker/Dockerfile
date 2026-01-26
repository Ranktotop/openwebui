# ---------------------------------------------------
# Morphik UI Dockerfile
# Exakt laut offizieller Doku: ee/ui-component
# ---------------------------------------------------

# 1️⃣ Base Image - Python, da Core Files schon drin sein sollen
FROM ghcr.io/morphik-org/morphik-core:latest AS base

# 2️⃣ Install Node.js (LTS)
# LTS Version 20, wie empfohlen von Next.js 14
RUN apt-get update && apt-get install -y curl build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 3️⃣ Set working directory in UI component
WORKDIR /app/ee/ui-component

# 4️⃣ Copy UI code (optional, falls du lokal Build nutzen willst)
# COPY ./ee/ui-component /app/ee/ui-component

# 5️⃣ Install Node dependencies
RUN npm install

# 6️⃣ Environment variable für API URL
# Muss zur Laufzeit im Compose überschrieben werden, hier nur default
ENV NEXT_PUBLIC_API_URL=http://morphik_server:8000

# 7️⃣ Optional: Watchpack Polling für Docker
ENV WATCHPACK_POLLING=true

# 8️⃣ Expose Next.js Dev Port
EXPOSE 3000

# 9️⃣ Start the UI in dev mode
CMD ["npm", "run", "dev"]
