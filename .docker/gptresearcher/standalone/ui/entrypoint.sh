#!/bin/sh
set -e

if [ -z "$NEXT_PUBLIC_GPTR_API_URL" ]; then
  echo "⚠️  WARNUNG: NEXT_PUBLIC_GPTR_API_URL ist nicht gesetzt."
  echo "   Nutze Standardwert: http://localhost:8000"
  export NEXT_PUBLIC_GPTR_API_URL="http://localhost:8000"
fi

export NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_GPTR_API_URL

# WebSocket-URL ableiten (http:// -> ws://, https:// -> wss://)
WS_URL=$(echo "$NEXT_PUBLIC_BACKEND_URL" | sed 's|^http://|ws://|' | sed 's|^https://|wss://|')

echo "🔧 Runtime-Konfiguration gestartet..."
echo "   HTTP Backend URL: $NEXT_PUBLIC_BACKEND_URL"
echo "   WebSocket URL: $WS_URL"

if [ "$NEXT_PUBLIC_BACKEND_URL" != "http://localhost:8000" ]; then
    # HTTP-URLs ersetzen
    find /app/.next -type f \( -name "*.js" -o -name "*.html" -o -name "*.json" \) -exec sed -i "s|http://localhost:8000|$NEXT_PUBLIC_BACKEND_URL|g" {} +
    # WebSocket-URLs ersetzen
    find /app/.next -type f \( -name "*.js" -o -name "*.html" -o -name "*.json" \) -exec sed -i "s|ws://localhost:8000|$WS_URL|g" {} +
    echo "✅ URLs erfolgreich ersetzt."
else
    echo "ℹ️  URL ist bereits localhost. Keine Änderung nötig."
fi

echo "🚀 Starte Anwendung..."
exec "$@"