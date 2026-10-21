# Две цели: dev (docker-compose.yml — тесты, линтер, автоперезагрузка)
# и prod (docker-compose.prod.yml — только рабочие зависимости, не root).
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt


FROM base AS dev

COPY requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

COPY . .

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]


FROM base AS prod

RUN useradd --system --no-create-home app
COPY --chown=app:app . .
USER app

# Миграции при старте, затем несколько процессов API (фоновые задачи — в сервисе worker).
# --proxy-headers: настоящий IP клиента от Caddy — по нему лимит попыток входа.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips='*'"]
