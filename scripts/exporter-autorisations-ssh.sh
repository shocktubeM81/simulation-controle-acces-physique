#!/bin/sh
# Commande forcée SSH : export lecture seule, jamais un shell.
set -eu
exec /usr/bin/curl --fail --silent --show-error --max-time 10 \
  --request POST http://127.0.0.1:3000/rpc/exporter_autorisations
