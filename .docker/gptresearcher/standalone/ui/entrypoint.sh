#!/bin/sh
set -e

if [ -z "$NEXT_PUBLIC_GPTR_API_URL" ]; then
  export NEXT_PUBLIC_GPTR_API_URL="http://localhost:8000"
fi

echo "🔧 Backend URL: $NEXT_PUBLIC_GPTR_API_URL"

# Liste Dateien VOR dem Ersetzen
echo "📋 Dateien mit Platzhalter VORHER:"
find /app/.next -type f \( -name "*.js" -o -name "*.json" \) -exec grep -l "http://dummyurl.local" {} + 2>/dev/null || echo "   Keine gefunden"

# Ersetze Platzhalter
echo "🔄 Ersetze Platzhalter..."
find /app/.next -type f \( -name "*.js" -o -name "*.json" \) -exec sed -i "s|http://dummyurl.local|${NEXT_PUBLIC_GPTR_API_URL}|g" {} +

# Prüfe NACHHER
echo "📋 Dateien mit Platzhalter NACHHER:"
find /app/.next -type f \( -name "*.js" -o -name "*.json" \) -exec grep -l "http://dummyurl.local" {} + 2>/dev/null || echo "   ✅ Alle ersetzt!"

echo "✅ Runtime-Config gesetzt"
exec "$@"