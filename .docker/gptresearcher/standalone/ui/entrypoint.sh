#!/bin/sh
set -e

if [ -z "$NEXT_PUBLIC_GPTR_API_URL" ]; then
  export NEXT_PUBLIC_GPTR_API_URL="http://localhost:8000"
fi

echo "🔧 Backend URL: $NEXT_PUBLIC_GPTR_API_URL"

# Ersetze Placeholder im kompilierten Code
find /app/.next -type f -name "*.js" -exec sed -i "s|http://dummyurl.local|${NEXT_PUBLIC_GPTR_API_URL}|g" {} +
sed -i "s|http://dummyurl.local|${NEXT_PUBLIC_GPTR_API_URL}|g" /app/next.config.mjs

echo "✅ Runtime-Config gesetzt"
exec "$@"