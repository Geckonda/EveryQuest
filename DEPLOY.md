# Деплой на сервер

Ежеквестик на VPS: Docker Compose, HTTPS от Let's Encrypt (Caddy), ежедневные бэкапы базы.
Все команды — на сервере, после `ssh root@94.232.42.149`.

```
интернет ──443──► web (Caddy: HTTPS, фронт, /api) ──► backend (API) ──► db (Postgres)
                                                       worker (штрафы, повторяющиеся)
                                                       backup (дамп раз в сутки → ./backups)
```

Наружу открыт только `web` (порты 80 и 443). База, API и воркер из интернета недоступны.

## 0. Безопасность сервера

Если пароль root куда-либо пересылали — смените его:

```sh
passwd
```

Удобнее и надёжнее входить по SSH-ключу. На своём компьютере (PowerShell):

```powershell
ssh-keygen -t ed25519            # Enter на все вопросы
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@94.232.42.149 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

После этого `ssh root@94.232.42.149` пускает без пароля.

## 1. Docker

```sh
docker --version && docker compose version
```

Если команды не найдены:

```sh
curl -fsSL https://get.docker.com | sh
```

## 2. Освободить порты 80 и 443

Посмотреть, что запущено:

```sh
docker ps --format 'table {{.Names}}\t{{.Ports}}'
ss -tlnp | grep -E ':(80|443) '
```

**Старое приложение (PlotCreator).** Узнать его папку и остановить:

```sh
docker inspect plotcreator-api --format '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}'
cd <папка из вывода>
# Если данные нужны — сначала дамп:
docker exec plotcreator-postgres pg_dump -U postgres PlotCreator > ~/plotcreator.sql
docker compose down        # контейнеры удалены, данные в томе остались
# docker compose down -v   # …или удалить и данные
```

**Если порт 80 или 443 занят nginx/apache на самом сервере** (видно в выводе `ss`):

```sh
systemctl disable --now nginx     # или apache2
```

**Файрвол.** Если включён `ufw` (`ufw status` показывает `active`):

```sh
ufw allow 80/tcp && ufw allow 443/tcp && ufw allow 443/udp
```

## 3. Код

```sh
git clone https://github.com/Geckonda/EveryQuest.git /opt/everyquest
cd /opt/everyquest
```

Если репозиторий приватный, git спросит логин и пароль: вместо пароля — токен GitHub
(Settings → Developer settings → Personal access tokens → Fine-grained, доступ на чтение к репозиторию).

## 4. Настройки

```sh
cp .env.prod.example .env
# Сгенерировать пароль базы и секрет токенов прямо в файл:
sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 32)|" .env
sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$(openssl rand -base64 48 | tr -d '\n')|" .env
cat .env
```

`DOMAIN` уже указан: `94-232-42-149.sslip.io` — этот адрес без всякой регистрации указывает
на IP сервера, и Let's Encrypt выдаёт для него сертификат. Появится свой домен — направьте его
A-запись на `94.232.42.149`, поменяйте `DOMAIN` в `.env` и выполните шаг 5 ещё раз.

`.env` хранит пароли — он только на сервере, в git не попадает. Пароль базы менять после
первого запуска нельзя: база уже создана со старым.

## 5. Запуск

```sh
docker compose -f docker-compose.prod.yml up -d --build
```

Первая сборка — несколько минут. Если сервер с 1 ГБ памяти и сборка фронта падает
(`Killed`, `exit code 137`), добавьте swap и повторите:

```sh
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

Проверить:

```sh
docker compose -f docker-compose.prod.yml ps        # backend и db — healthy, остальные — running
docker compose -f docker-compose.prod.yml logs web  # «certificate obtained successfully»
```

Открыть **https://94-232-42-149.sslip.io** и зарегистрироваться.

## Обновление

```sh
cd /opt/everyquest
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Миграции базы применяются сами при старте API.

## Бэкапы

Сервис `backup` раз в сутки кладёт дамп в `/opt/everyquest/backups` и удаляет старше
`BACKUP_KEEP_DAYS` (14 дней).

**Проверка раз в месяц** — дамп разворачивается во временную базу, боевая не трогается:

```sh
cd /opt/everyquest
scripts/restore.sh --check backups/$(ls -t backups | head -1)
```

**Восстановление** (всё, что изменилось после дампа, пропадёт; спросит подтверждение):

```sh
scripts/restore.sh --replace backups/everyquest_ГГГГ-ММ-ДД_ЧЧММ.dump
```

**Копия вне сервера.** Дамп на том же сервере не спасёт, если пропадёт сам сервер.
Скачивать к себе (PowerShell на своём компьютере):

```powershell
scp "root@94.232.42.149:/opt/everyquest/backups/*.dump" D:\backups\everyquest\
```

## Если что-то не так

| Симптом | Что смотреть |
| --- | --- |
| Сайт не открывается, сертификата нет | `logs web`: порт 80 должен быть свободен и открыт в файрволе — через него Let's Encrypt проверяет домен |
| «JWT_SECRET не задан или короче 32 символов» в `logs backend` | Шаг 4: секрет в `.env` не заполнен |
| `required variable … is missing a value` | В `.env` пустая строка для этой переменной |
| Вход не держится, выкидывает после перезагрузки | Открыт ли сайт по **https**; по http cookie входа не сохраняется |
| Штрафы не списываются | `docker compose -f docker-compose.prod.yml logs worker` |

Логи любого сервиса: `docker compose -f docker-compose.prod.yml logs -f <db|backend|worker|web|backup>`.
