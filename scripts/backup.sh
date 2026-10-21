#!/bin/sh
# Ежедневный дамп базы (сервис backup в docker-compose.prod.yml).
# Подключение — из PGHOST/PGUSER/PGPASSWORD/PGDATABASE. Дампы — в /backups (./backups на сервере).
set -eu

KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"

dump() {
	stamp="$(date -u +%Y-%m-%d_%H%M)"
	file="/backups/everyquest_${stamp}.dump"
	# Сначала во временный файл: оборванный дамп не должен выглядеть как готовый.
	if pg_dump --format=custom --file="${file}.tmp"; then
		mv "${file}.tmp" "${file}"
		echo "backup: готово ${file} ($(du -h "${file}" | cut -f1))"
	else
		rm -f "${file}.tmp"
		echo "backup: ОШИБКА дампа" >&2
	fi
	find /backups -name 'everyquest_*.dump' -mtime "+${KEEP_DAYS}" -delete
}

# Сразу при старте и затем раз в сутки.
while true; do
	dump
	sleep 86400
done
