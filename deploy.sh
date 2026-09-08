#!/bin/bash

set -e

echo "=== Deploy Magno Figures ==="

echo ">> Buildando e iniciando containers..."
docker compose up -d --build

echo ">> Aplicando migrações..."
docker compose exec web python manage.py migrate

echo ">> Coletando arquivos estáticos..."
docker compose exec web python manage.py collectstatic --noinput

echo "=== Deploy concluído com sucesso! ==="
