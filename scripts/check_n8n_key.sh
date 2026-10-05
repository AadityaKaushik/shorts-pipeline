#!/bin/bash
# Compares N8N_ENCRYPTION_KEY in .env with the key n8n actually uses.
# Prints only MATCH / MISMATCH and key lengths — never the keys themselves.
cd "$(dirname "$0")/.."
envkey=$(grep '^N8N_ENCRYPTION_KEY=' .env | cut -d= -f2-)
n8nkey=$(docker compose exec -T n8n cat /home/node/.n8n/config | sed -n 's/.*"encryptionKey": *"\([^"]*\)".*/\1/p')
echo "env key length:  ${#envkey}"
echo "n8n key length:  ${#n8nkey}"
if [ -z "$envkey" ]; then
    echo ENV_EMPTY
elif [ -z "$n8nkey" ]; then
    echo "N8N_KEY_NOT_FOUND (config file format may differ)"
elif [ "$envkey" = "$n8nkey" ]; then
    echo MATCH
else
    echo MISMATCH
fi
