#!/usr/bin/env bash
# Shell script de orquestração — atende ao requisito de "shell script" do enunciado.
# Executa a simulação nos três modos e salva logs com timestamp.

set -euo pipefail

cd "$(dirname "$0")/src"

LOG_DIR="../logs"
mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"

echo "==> Modo: default"
python3 main.py default | tee "$LOG_DIR/default_$STAMP.log"

echo "==> Modo: custom"
python3 main.py custom  | tee "$LOG_DIR/custom_$STAMP.log"

echo "==> Modo: compare"
python3 main.py compare | tee "$LOG_DIR/compare_$STAMP.log"

echo "Logs salvos em $LOG_DIR/"
