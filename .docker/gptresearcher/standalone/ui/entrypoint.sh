#!/bin/sh
set -e

# 1. Prüfen, ob die Variable gesetzt ist. Falls nicht, Standard beibehalten.
if [ -z "$NEXT_PUBLIC_GPTR_API_URL" ]; then
  echo "⚠️  WARNUNG: NEXT_PUBLIC_GPTR_API_URL ist nicht gesetzt."
  echo "   Nutze Standardwert: http://localhost:8000"
  export NEXT_PUBLIC_GPTR_API_URL="http://localhost:8000"
fi

# Wir setzen die Ziel-URL
export NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_GPTR_API_URL

echo "🔧 Runtime-Konfiguration gestartet..."
echo "   Ziel Backend URL: $NEXT_PUBLIC_BACKEND_URL"

# 2. Suchen und Ersetzen
# WICHTIG: Wir ersetzen jetzt 'http://localhost:8000' (den Build-Wert) durch die echte URL.
# Wenn die echte URL auch localhost ist, passiert einfach nichts (was ok ist).
if [ "$NEXT_PUBLIC_BACKEND_URL" != "http://localhost:8000" ]; then
    find /app/.next -type f \( -name "*.js" -o -name "*.html" -o -name "*.json" \) -exec sed -i "s|http://localhost:8000|$NEXT_PUBLIC_BACKEND_URL|g" {} +
    echo "✅ URL erfolgreich von localhost auf $NEXT_PUBLIC_BACKEND_URL geändert."
else
    echo "ℹ️  URL ist bereits localhost. Keine Änderung nötig."
fi

echo "🚀 Starte Anwendung..."
exec "$@"