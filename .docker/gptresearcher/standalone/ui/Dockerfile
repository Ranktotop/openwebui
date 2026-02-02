###############################################
# 0) Cloner layer (Extra für dich)
###############################################
FROM node:18.17.0-alpine AS cloner
WORKDIR /temp
RUN apk add --no-cache git
RUN git clone https://github.com/assafelovic/gpt-researcher.git .

###############################################
# 1) Dependencies layer
###############################################
FROM node:18.17.0-alpine AS deps
WORKDIR /app

# Copy only package manifest from CLONER
COPY --from=cloner /temp/frontend/nextjs/package.json ./

# Install dependencies
RUN npm install --legacy-peer-deps

###############################################
# 2) Builder layer
###############################################
FROM node:18.17.0-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules

# Copy source code from CLONER
COPY --from=cloner /temp/frontend/nextjs ./

# Im Builder layer nach dem COPY:
RUN sed -i 's|NEXT_PUBLIC_BACKEND_URL|NEXT_PUBLIC_GPTR_API_URL|g' next.config.mjs

# Build-Argument mit Default
ARG NEXT_PUBLIC_GPTR_API_URL=http://dummyurl.local
ENV NEXT_PUBLIC_GPTR_API_URL=${NEXT_PUBLIC_GPTR_API_URL}

# Build Next.js application
RUN npm run build

###############################################
# 3) Runner layer
###############################################
FROM node:18.17.0-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Copy only what is required at runtime (Exakt wie im Original)
COPY --from=builder /app/package.json ./
COPY --from=builder /app/next.config.mjs ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules

# Runtime-Config Script
COPY .docker/gptresearcher/standalone/ui/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 3000

ENTRYPOINT ["/app/entrypoint.sh"]
# Start command (Exakt wie im Original)
CMD ["npm", "run", "start"]