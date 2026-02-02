#!/bin/sh
set -e

# 1. Prüfen, ob die Variable gesetzt ist. Falls nicht, Fallback nutzen.
if [ -z "$NEXT_PUBLIC_GPTR_API_URL" ]; then
  echo "⚠️  WARNUNG: NEXT_PUBLIC_BACKEND_URL ist nicht gesetzt."
  echo "   Nutze Standardwert: http://localhost:8000"
  export NEXT_PUBLIC_GPTR_API_URL="http://localhost:8000"
fi
export NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_GPTR_API_URL
echo "🔧 Runtime-Konfiguration gestartet..."
echo "   Ziel Backend URL: $NEXT_PUBLIC_BACKEND_URL"

# 2. Suchen und Ersetzen (Magic)
# Wir durchsuchen den kompilierten .next Ordner nach dem Platzhalter.
# Wir suchen in JS, HTML und JSON Dateien, um sicherzugehen, dass wir alles erwischen.
# Wir nutzen '|' als Trennzeichen für sed, da URLs '/' enthalten.
find /app/.next -type f \( -name "*.js" -o -name "*.html" -o -name "*.json" \) -exec sed -i "s|BUILD_TIME_BACKEND_URL|$NEXT_PUBLIC_BACKEND_URL|g" {} +

echo "✅ URL erfolgreich ersetzt."
echo "🚀 Starte Anwendung..."

# 3. Führe den eigentlichen Docker CMD Befehl aus (npm run start)
exec "$@"