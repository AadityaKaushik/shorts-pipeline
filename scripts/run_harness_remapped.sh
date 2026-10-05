#!/bin/bash
# TEMPORARY: run the harness with the two denied keys remapped to working ones.
# Delete once the owner replaces GEMINI_API_KEY_TOPIC and GEMINI_API_KEY_SCRIPT_CHECK.
cd "$(dirname "$0")/.."
set -a
. ./.env
set +a
export GEMINI_API_KEY_TOPIC="$GEMINI_API_KEY_METADATA"
export GEMINI_API_KEY_SCRIPT_CHECK="$GEMINI_API_KEY_CODE"
exec python3 pipeline_test.py "$@"
