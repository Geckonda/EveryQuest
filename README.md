# Ежеквестик

Органайзер, где задачи — квесты с наградой в монетах, а развлечения — траты. Что умеет приложение — [FEATURES.md](FEATURES.md). План: [Ежеквестик — план MVP.md](Ежеквестик%20—%20план%20MVP.md).

## Запуск

```sh
cp .env.example .env   # по желанию: порты, пароли, JWT_SECRET
docker compose up -d --build
```

- Фронтенд: http://localhost:5175
- API: http://localhost:8000/api/v1, документация — http://localhost:8000/docs
- Postgres: localhost:5432 (everyquest / everyquest)

Миграции применяются автоматически при старте бэкенда. Код бэкенда и фронта смонтирован в контейнеры, изменения подхватываются на лету.

Фоновые задачи (штрафы за просрочку, генерация повторяющихся квестов) выполняет отдельный сервис `worker` (`python -m app.worker`) раз в 5 минут и сразу при старте. Он стартует после того, как бэкенд накатил миграции. Код воркера на лету не перезагружается — после правок `app/jobs.py` или `app/scheduler.py`: `docker compose restart worker`. Без docker задачи можно запустить внутри API: `SCHEDULER_ENABLED=true`.

## Прод

Сервер: `docker-compose.prod.yml` — HTTPS (Caddy), прод-сборки, бэкапы. Пошагово — [DEPLOY.md](DEPLOY.md).

## Структура

```
backend/    FastAPI + SQLAlchemy 2.0 + Alembic
  app/        приложение (models.py — схема БД)
  alembic/    миграции
  tests/
frontend/   Vue 3 + Vite + TypeScript + Pinia + Vue Router
```

## Команды

Бэкенд (в контейнере):

```sh
docker compose exec backend ruff check . && docker compose exec backend ruff format .
docker compose exec backend pytest
docker compose exec backend alembic revision --autogenerate -m "описание"
docker compose exec backend alembic upgrade head
```

Фронтенд (локально, из `frontend/`):

```sh
npm run lint        # oxlint + eslint
npm run format      # prettier
npm run test:unit
npm run build
```

После добавления npm-пакета пересоберите контейнер фронта с новым томом `node_modules`:

```sh
docker compose up -d --build --renew-anon-volumes frontend
```

Если `npm install` падает с `Cannot read properties of null (reading 'edgesOut')` — это баг npm 10, используйте `npx npm@11 install`.
