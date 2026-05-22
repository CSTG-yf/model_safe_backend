#!/bin/sh
set -e

ollama serve &
pid="$!"

sleep 5
ollama pull "${OLLAMA_EMBEDDING_MODEL:-bge-m3}" || true

wait "$pid"
