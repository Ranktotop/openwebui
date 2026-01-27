#!/bin/sh
set -e

# Setze Defaults falls nicht gesetzt
export UI_HOST=${UI_HOST:-morphik_ui}
export UI_PORT=${UI_PORT:-3000}
export API_HOST=${API_HOST:-morphik_server}
export API_PORT=${API_PORT:-8000}
export MAX_UPLOAD_SIZE=${MAX_UPLOAD_SIZE:-500M}
export PROXY_TIMEOUT=${PROXY_TIMEOUT:-300s}

echo "==================================="
echo "Nginx Reverse Proxy Configuration"
echo "==================================="
echo "UI:  ${UI_HOST}:${UI_PORT}"
echo "API: ${API_HOST}:${API_PORT}"
echo "Max Upload: ${MAX_UPLOAD_SIZE}"
echo "Proxy Timeout: ${PROXY_TIMEOUT}"
echo "==================================="

# Ersetze Platzhalter im Template
envsubst '${UI_HOST} ${UI_PORT} ${API_HOST} ${API_PORT} ${MAX_UPLOAD_SIZE} ${PROXY_TIMEOUT}' \
  < /etc/nginx/nginx.conf.template \
  > /etc/nginx/nginx.conf

# Zeige generierte Config (für Debugging)
echo "Generated nginx.conf:"
cat /etc/nginx/nginx.conf

# Teste nginx Config
nginx -t

# Starte nginx
exec "$@"