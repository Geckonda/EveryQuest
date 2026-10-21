#!/bin/sh
# Восстановление из дампа. Запускать на сервере из папки проекта.
#
#   scripts/restore.sh --check backups/everyquest_2026-10-22_0300.dump
#       проверить дамп: развернуть во временную базу, показать число строк, удалить её.
#       Боевую базу не трогает. Стоит делать раз в месяц: бэкап, который ни разу
#       не восстанавливали, бэкапом не считается.
#
#   scripts/restore.sh --replace backups/everyquest_2026-10-22_0300.dump
#       заменить боевую базу дампом. Всё, что изменилось после дампа, пропадёт.
set -eu

COMPOSE="docker compose -f docker-compose.prod.yml"
MODE="${1:-}"
FILE="${2:-}"

if [ -z "$MODE" ] || [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
	sed -n '2,12p' "$0"
	exit 1
fi

# Имя пользователя и базы — как в .env (по умолчанию everyquest).
if [ -f .env ]; then
	set -a
	. ./.env
	set +a
fi
PG_USER="${POSTGRES_USER:-everyquest}"
PG_DB="${POSTGRES_DB:-everyquest}"

psql_in_db() {
	$COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -U "$PG_USER" "$@"
}

case "$MODE" in
--check)
	TMP_DB="restore_check"
	psql_in_db -d postgres -c "DROP DATABASE IF EXISTS $TMP_DB" -c "CREATE DATABASE $TMP_DB"
	$COMPOSE exec -T db pg_restore --no-owner -U "$PG_USER" -d "$TMP_DB" <"$FILE"
	psql_in_db -d "$TMP_DB" -c "
		SELECT 'users' AS таблица, count(*) FROM users
		UNION ALL SELECT 'quests', count(*) FROM quests
		UNION ALL SELECT 'transactions', count(*) FROM transactions
		UNION ALL SELECT 'rewards', count(*) FROM rewards"
	psql_in_db -d postgres -c "DROP DATABASE $TMP_DB"
	echo "Проверка прошла: дамп разворачивается."
	;;
--replace)
	printf 'Заменить боевую базу дампом %s? Изменения после дампа пропадут. [yes/N] ' "$FILE"
	read -r answer
	[ "$answer" = "yes" ] || { echo "Отменено."; exit 1; }
	# Останавливаем API и воркер, чтобы никто не писал в базу во время замены.
	$COMPOSE stop backend worker
	$COMPOSE exec -T db pg_restore --clean --if-exists --no-owner -U "$PG_USER" -d "$PG_DB" <"$FILE"
	$COMPOSE start backend worker
	echo "Готово: база восстановлена из $FILE."
	;;
*)
	sed -n '2,12p' "$0"
	exit 1
	;;
esac
