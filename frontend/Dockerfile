# Две цели: dev (docker-compose.yml — Vite с автоперезагрузкой)
# и prod (docker-compose.prod.yml — собранный фронт, который отдаёт Caddy с HTTPS).
FROM node:22-slim AS dev

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]


FROM dev AS build

RUN npm run build-only


# Caddy: сам получает и продлевает сертификат Let's Encrypt, отдаёт статику
# и проксирует /api в бэкенд. Единственный сервис, открытый в интернет.
FROM caddy:2.8-alpine AS prod

COPY --from=build /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile
