#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."
git pull origin main
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py check

if command -v pm2 >/dev/null 2>&1; then
  pm2 restart questlab-api || pm2 start "python manage.py runserver 0.0.0.0:8000" --name questlab-api
fi
