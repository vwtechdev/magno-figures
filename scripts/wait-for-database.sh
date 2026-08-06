#!/bin/bash

set -e

HOST="${POSTGRES_HOST:-db}"
PORT="${POSTGRES_PORT:-5432}"
USER="${POSTGRES_USER:-postgres}"
MAX_ATTEMPTS=30
ATTEMPT=1

echo "Waiting for PostgreSQL at $HOST:$PORT..."

until pg_isready -h "$HOST" -p "$PORT" -U "$USER" > /dev/null 2>&1; do
    if [ "$ATTEMPT" -ge "$MAX_ATTEMPTS" ]; then
        echo "PostgreSQL não disponível após $MAX_ATTEMPTS tentativas. Saindo."
        exit 1
    fi
    echo "Tentativa $ATTEMPT/$MAX_ATTEMPTS - aguardando PostgreSQL..."
    sleep 2
    ATTEMPT=$((ATTEMPT + 1))
done

echo "PostgreSQL disponível. Continuando..."
exec "$@"
