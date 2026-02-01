FROM node:18.17.0-alpine AS cloner
WORKDIR /temp
RUN apk add --no-cache git
RUN git clone https://github.com/assafelovic/gpt-researcher.git ./

FROM node:18.17.0-alpine
WORKDIR /app
COPY --from=cloner /temp/gpt-researcher/frontend/nextjs ./
RUN npm install --legacy-peer-deps
CMD ["npm", "run", "dev"]