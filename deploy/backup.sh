#!/usr/bin/env bash
# Nightly backup for cPanel cron. Edit the variables, chmod 700 this file, test it once by hand.
# Example cron (02:30 daily):  30 2 * * * /home/USER/ispon/deploy/backup.sh >> /home/USER/backups/backup.log 2>&1
set -euo pipefail
APP=/home/USER/ispon
OUT=/home/USER/backups            # keep this OUTSIDE public_html
KEEP_DAYS=30
GPG_RECIPIENT=""                  # optional: gpg key id/email to encrypt backups with
mkdir -p "$OUT"; chmod 700 "$OUT"
STAMP=$(date +%Y%m%d-%H%M%S)
cd "$APP"
set -a; source .env; set +a
case "${DB_ENGINE:-sqlite}" in
  postgres) PGPASSWORD="$DB_PASSWORD" pg_dump -h "${DB_HOST:-localhost}" -U "$DB_USER" "$DB_NAME" > "$OUT/db-$STAMP.sql" ;;
  mysql)    MYSQL_PWD="$DB_PASSWORD" mysqldump -h "${DB_HOST:-localhost}" -u "$DB_USER" --single-transaction "$DB_NAME" > "$OUT/db-$STAMP.sql" ;;
  *)        cp db.sqlite3 "$OUT/db-$STAMP.sqlite3" ;;
esac
tar -czf "$OUT/media-$STAMP.tar.gz" -C "$APP" media
if [ -n "$GPG_RECIPIENT" ]; then
  for f in "$OUT"/db-$STAMP.* "$OUT"/media-$STAMP.tar.gz; do gpg --batch --yes -r "$GPG_RECIPIENT" -e "$f" && rm "$f"; done
fi
find "$OUT" -type f -mtime +$KEEP_DAYS -delete
echo "backup $STAMP done"
