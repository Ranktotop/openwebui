#!/bin/sh
set -e

FILE="pkg/openwebui/client.go"

echo "Fixing OpenWebUI API pagination in $FILE..."

# Prüfe ob die Datei existiert
if [ ! -f "$FILE" ]; then
    echo "ERROR: $FILE not found!"
    exit 1
fi

# Füge KnowledgeListResponse struct hinzu (nach Knowledge struct)
sed -i '/^type Knowledge struct {/,/^}/a\
\
// KnowledgeListResponse represents the paginated response from OpenWebUI API v0.6.42+\
type KnowledgeListResponse struct {\
\tItems []*Knowledge `json:"items"`\
\tTotal int          `json:"total"`\
}' "$FILE"

# Ändere ListKnowledge Funktion: var knowledge -> var response
sed -i 's/var knowledge \[\]\*Knowledge/var response KnowledgeListResponse/g' "$FILE"

# Ändere ListKnowledge Funktion: Decode(&knowledge) -> Decode(&response)
sed -i 's/Decode(&knowledge)/Decode(\&response)/g' "$FILE"

# Ändere ListKnowledge Funktion: return knowledge -> return response.Items
sed -i 's/return knowledge, nil/return response.Items, nil/g' "$FILE"

echo "✓ Fixed API pagination support"