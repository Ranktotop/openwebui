# GPT-Researcher Queue Server

Ein Middleware-Service, der Research-Anfragen in eine Queue einreiht und die Anzahl paralleler Recherchen limitiert.

## 🎯 Features

- ✅ **Queue-Management**: Max. 1 parallele Research (konfigurierbar)
- ✅ **Status-Proxy**: Zeigt "Waiting..."-Status bei voller Queue
- ✅ **Live-Streaming**: Leitet Live-Status von GPT-Researcher durch
- ✅ **WebSocket-basiert**: Real-time Kommunikation
- ✅ **Health Checks**: Status-Endpoints für Monitoring

## 🏗️ Architektur

```
OpenWebUI Pipeline → Queue-Server (Port 8001) → GPT-Researcher (Port 8000)
                        ├── Queue (max 1 parallel)
                        ├── Status: "Waiting..." wenn voll
                        └── Status: Live-Proxy wenn Research läuft
```

## 🚀 Schnellstart

### 1. Vorbereitung

```bash
# .env Datei erstellen
cp .env.queue.example .env

# API Keys eintragen
nano .env
```

### 2. Mit Docker Compose starten

```bash
# Services starten
docker-compose -f docker-compose.queue.yaml up --build

# Services im Hintergrund starten
docker-compose -f docker-compose.queue.yaml up -d --build
```

### 3. Services überprüfen

```bash
# Health Check
curl http://localhost:8001/

# Queue Status
curl http://localhost:8001/status
```

**Erwartete Antwort:**

```json
{
  "status": "ok",
  "service": "gpt-researcher-queue-server",
  "version": "1.0.0",
  "queue_size": 0,
  "active_tasks": 0,
  "max_concurrent": 1
}
```

## 🧪 Testen

### Mit dem Test-Script

```bash
# Abhängigkeiten installieren
pip install websockets aiohttp

# Tests ausführen
python test_queue_server.py
```

### Manuell mit wscat

```bash
# wscat installieren
npm install -g wscat

# Verbindung zum Queue-Server
wscat -c ws://localhost:8001/ws

# Dann JSON senden:
{
  "task": "Why is Nvidia stock going up?",
  "report_type": "research_report",
  "report_source": "web",
  "tone": "Objective",
  "verbose": true
}
```

### Mit Python

```python
import asyncio
import websockets
import json

async def test_queue():
    uri = "ws://localhost:8001/ws"

    async with websockets.connect(uri) as websocket:
        # Send request
        request = {
            "task": "What is quantum computing?",
            "report_type": "research_report",
            "report_source": "web",
            "tone": "Objective",
            "verbose": True
        }
        await websocket.send(json.dumps(request))

        # Receive messages
        async for message in websocket:
            data = json.loads(message)
            print(f"[{data['type']}] {data['content'][:100]}")

            if data['type'] == 'report':
                print("✅ Research complete!")
                break

asyncio.run(test_queue())
```

## 📊 Queue-Verhalten testen

### Test 1: Einzelne Request

```bash
# Terminal 1
wscat -c ws://localhost:8001/ws
{"task": "Test Query 1", "report_type": "research_report"}
```

**Erwartetes Verhalten:**

- Sofort gestartet ✅
- Live-Status von GPT-Researcher ✅

### Test 2: Mehrere gleichzeitige Requests

```bash
# Terminal 1
wscat -c ws://localhost:8001/ws
{"task": "Test Query 1", "report_type": "research_report"}

# Terminal 2 (während Query 1 läuft)
wscat -c ws://localhost:8001/ws
{"task": "Test Query 2", "report_type": "research_report"}
```

**Erwartetes Verhalten:**

- **Terminal 1**: Sofort gestartet ✅
- **Terminal 2**:
  - `"⏳ Waiting for available research slot... Position in queue: 1"` ✅
  - Startet automatisch nach Abschluss von Query 1 ✅

## 🔧 Konfiguration

### Environment Variables

| Variable                   | Default                             | Beschreibung                  |
| -------------------------- | ----------------------------------- | ----------------------------- |
| `MAX_CONCURRENT_RESEARCH`  | `1`                                 | Max. parallele Research-Tasks |
| `GPTRESEARCHER_QUEUE_PORT` | `8001`                              | Queue-Server Port             |
| `GPTRESEARCHER_WS_URL`     | `ws://gptresearcher-server:8000/ws` | GPT-Researcher WebSocket URL  |

### Ändern der maximalen parallelen Recherchen

```bash
# In .env
MAX_CONCURRENT_RESEARCH=2

# Neustart
docker-compose -f docker-compose.queue.yaml restart gptresearcher-queue
```

## 📡 API Endpoints

### WebSocket `/ws`

**Request Format:**

```json
{
  "task": "Your research query",
  "report_type": "research_report",
  "report_source": "web",
  "tone": "Objective",
  "verbose": true
}
```

**Response Messages:**

1. **Waiting Status** (wenn Queue voll)

```json
{
  "type": "logs",
  "content": "⏳ Waiting for available research slot... Position in queue: 1",
  "metadata": {
    "status": "waiting",
    "queue_position": 1,
    "timestamp": "2025-02-01T10:00:00"
  }
}
```

2. **Queued Confirmation**

```json
{
  "type": "logs",
  "content": "✅ Request queued successfully. Research will start shortly...",
  "metadata": {
    "status": "queued",
    "timestamp": "2025-02-01T10:00:05"
  }
}
```

3. **Live Research Status** (von GPT-Researcher durchgereicht)

```json
{
  "type": "logs",
  "content": "🤔 Planning research strategy...",
  "metadata": {...}
}
```

### REST Endpoints

#### `GET /`

Health Check

**Response:**

```json
{
  "status": "ok",
  "service": "gpt-researcher-queue-server",
  "version": "1.0.0",
  "queue_size": 0,
  "active_tasks": 0,
  "max_concurrent": 1
}
```

#### `GET /status`

Queue Status

**Response:**

```json
{
  "queue_size": 0,
  "active_tasks": 0,
  "max_concurrent": 1,
  "available_slots": 1
}
```

## 🐛 Troubleshooting

### Queue-Server startet nicht

```bash
# Logs prüfen
docker-compose -f docker-compose.queue.yaml logs gptresearcher-queue

# Container status
docker-compose -f docker-compose.queue.yaml ps
```

### Connection Error zu GPT-Researcher

**Problem:** `Connection to GPT-Researcher failed`

**Lösung:**

```bash
# Prüfen ob GPT-Researcher läuft
docker-compose -f docker-compose.queue.yaml logs gptresearcher-server

# Network prüfen
docker network inspect gptresearcher-network
```

### Research bleibt in Queue stecken

```bash
# Status prüfen
curl http://localhost:8001/status

# Falls active_tasks > 0 aber nichts passiert:
docker-compose -f docker-compose.queue.yaml restart gptresearcher-queue
```

## 📝 Logs

```bash
# Alle Services
docker-compose -f docker-compose.queue.yaml logs -f

# Nur Queue-Server
docker-compose -f docker-compose.queue.yaml logs -f gptresearcher-queue

# Nur GPT-Researcher
docker-compose -f docker-compose.queue.yaml logs -f gptresearcher-server
```

## 🔄 Services verwalten

```bash
# Starten
docker-compose -f docker-compose.queue.yaml up -d

# Stoppen
docker-compose -f docker-compose.queue.yaml down

# Neustart
docker-compose -f docker-compose.queue.yaml restart

# Neu bauen
docker-compose -f docker-compose.queue.yaml up --build -d
```

## 🎯 Nächste Schritte

Nach erfolgreichem Test des Queue-Servers:

1. ✅ **Queue-Server läuft** - Du bist hier!
2. ⏭️ **OpenWebUI Pipeline erstellen** - Nächster Schritt
3. ⏭️ **Integration testen** - End-to-End Test
4. ⏭️ **Production Deployment** - Finale Integration

## 📚 Weitere Ressourcen

- [GPT-Researcher Dokumentation](https://docs.gptr.dev)
- [GPT-Researcher API Dokumentation](./GPT_RESEARCHER_API.md)
- [FastAPI Dokumentation](https://fastapi.tiangolo.com)
