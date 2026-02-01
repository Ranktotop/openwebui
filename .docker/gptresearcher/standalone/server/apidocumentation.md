# GPT-Researcher API Documentation

**Version:** 0.14.5  
**Base URL:** `http://localhost:8000` (default)  
**Protocol:** FastAPI with WebSocket support

---

## Overview

GPT-Researcher exposes a FastAPI-based backend that supports both REST endpoints and WebSocket connections for real-time research streaming. The primary communication method for the web UI is via WebSocket at `/ws`.

---

## Endpoints

### 1. WebSocket Endpoint (Primary)

**WebSocket URL:** `ws://localhost:8000/ws`

This is the main endpoint used by the frontend for real-time research streaming.

#### Connection Flow

```javascript
const socket = new WebSocket("ws://localhost:8000/ws");

socket.onopen = () => {
  console.log("Connected to GPT-Researcher");
};

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Received:", data);
};

socket.onerror = (error) => {
  console.error("WebSocket error:", error);
};

socket.onclose = () => {
  console.log("Disconnected from GPT-Researcher");
};
```

#### Message Format (Client → Server)

The client sends a JSON message to initiate research:

```json
{
  "task": "Your research query here",
  "report_type": "research_report",
  "report_source": "web",
  "source_urls": [],
  "tone": "Objective",
  "headers": {},
  "verbose": true
}
```

**Parameters:**

| Parameter       | Type    | Required | Default             | Description                                                                                                                                                                                                                                                    |
| --------------- | ------- | -------- | ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `task`          | string  | Yes      | -                   | The research query/question                                                                                                                                                                                                                                    |
| `report_type`   | string  | No       | `"research_report"` | Type of report (see Report Types below)                                                                                                                                                                                                                        |
| `report_source` | string  | No       | `"web"`             | Source for research: `"web"`, `"local"`, `"hybrid"`                                                                                                                                                                                                            |
| `source_urls`   | array   | No       | `[]`                | Specific URLs to research (optional)                                                                                                                                                                                                                           |
| `tone`          | string  | No       | `"Objective"`       | Tone of the report: `"Objective"`, `"Formal"`, `"Analytical"`, `"Persuasive"`, `"Informative"`, `"Explanatory"`, `"Descriptive"`, `"Critical"`, `"Comparative"`, `"Speculative"`, `"Reflective"`, `"Narrative"`, `"Humorous"`, `"Optimistic"`, `"Pessimistic"` |
| `headers`       | object  | No       | `{}`                | Custom HTTP headers for web scraping                                                                                                                                                                                                                           |
| `verbose`       | boolean | No       | `true`              | Enable detailed logging                                                                                                                                                                                                                                        |

#### Report Types

- `"research_report"` - Standard comprehensive research report
- `"detailed_report"` - More detailed analysis
- `"resource_report"` - Focus on gathering resources/sources
- `"outline_report"` - Structured outline format
- `"custom_report"` - Custom formatted report
- `"deep"` - Deep recursive research (5+ minutes, experimental)

#### Message Format (Server → Client)

The server streams multiple message types during research:

##### 1. Logs (Research Progress)

```json
{
  "type": "logs",
  "content": "🤔 Planning research strategy...",
  "metadata": {
    "step": "planning",
    "timestamp": "2025-02-01T10:00:00Z"
  }
}
```

##### 2. Path (Research Questions)

```json
{
  "type": "path",
  "content": "What are the key factors driving Nvidia stock performance?",
  "metadata": {
    "question_number": 1,
    "total_questions": 5
  }
}
```

##### 3. Report (Final Output)

```json
{
  "type": "report",
  "content": "# Research Report: Why is Nvidia Stock Going Up?\n\n## Introduction\n...",
  "metadata": {
    "sources": [
      { "url": "https://example.com/article1", "title": "..." },
      { "url": "https://example.com/article2", "title": "..." }
    ],
    "images": ["https://example.com/image1.png"],
    "report_type": "research_report",
    "word_count": 2500,
    "research_duration_seconds": 180
  }
}
```

##### 4. Error Messages

```json
{
  "type": "error",
  "content": "Error message description",
  "metadata": {
    "error_code": "RATE_LIMIT_EXCEEDED",
    "retry_after": 60
  }
}
```

---

### 2. Health Check Endpoint (Optional)

**Method:** `GET`  
**Endpoint:** `/`  
**Response:**

```json
{
  "status": "ok",
  "message": "GPT-Researcher API is running"
}
```

---

## Configuration (Environment Variables)

Research behavior is configured via environment variables:

### LLM Configuration

```bash
# OpenAI (recommended)
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional for custom endpoints

# LLM Models
FAST_LLM=openai:gpt-4o-mini           # For quick tasks
SMART_LLM=openai:gpt-4o               # For main research
STRATEGIC_LLM=openai:o1-preview       # For planning/strategy
EMBEDDING=openai:text-embedding-3-large
```

### Search Configuration

```bash
# Search Provider
RETRIEVER=tavily  # Options: tavily, google, bing, duckduckgo, serper, searx, mcp

# Tavily API (recommended)
TAVILY_API_KEY=tvly-...

# Alternative search providers
GOOGLE_API_KEY=...
GOOGLE_CX_KEY=...
BING_API_KEY=...
SERPER_API_KEY=...
```

### Research Behavior

```bash
# Report settings
TOTAL_WORDS=1000              # Target word count
MAX_ITERATIONS=3              # Research depth per subtopic
MAX_SUBTOPICS=3              # Number of research questions
TEMPERATURE=0.55             # LLM creativity (0.0-1.0)

# Deep Research (experimental)
DEEP_RESEARCH_BREADTH=2      # Parallel research paths
DEEP_RESEARCH_DEPTH=2        # Research tree depth
DEEP_RESEARCH_CONCURRENCY=4  # Max parallel operations

# Local documents
DOC_PATH=/path/to/documents  # For local research

# Language
LANGUAGE=english
```

---

## Status Message Types Reference

During WebSocket streaming, the server sends different message types:

| Type     | Purpose                      | Frequency     |
| -------- | ---------------------------- | ------------- |
| `logs`   | Research progress updates    | Continuous    |
| `path`   | Research questions/subtopics | Per question  |
| `report` | Final research output        | Once (at end) |
| `error`  | Error information            | On error      |

---

## Example: Complete Research Flow

### JavaScript/TypeScript Example

```javascript
async function conductResearch(query) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket("ws://localhost:8000/ws");
    let finalReport = null;
    const logs = [];
    const questions = [];

    socket.onopen = () => {
      // Send research request
      socket.send(
        JSON.stringify({
          task: query,
          report_type: "research_report",
          report_source: "web",
          tone: "Objective",
          verbose: true,
        }),
      );
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case "logs":
          console.log("📊", data.content);
          logs.push(data.content);
          break;

        case "path":
          console.log("🔍", data.content);
          questions.push(data.content);
          break;

        case "report":
          console.log("✅ Research complete!");
          finalReport = data;
          socket.close();
          break;

        case "error":
          console.error("❌", data.content);
          reject(new Error(data.content));
          break;
      }
    };

    socket.onclose = () => {
      if (finalReport) {
        resolve({
          report: finalReport.content,
          metadata: finalReport.metadata,
          logs,
          questions,
        });
      } else {
        reject(new Error("Connection closed without report"));
      }
    };

    socket.onerror = (error) => {
      reject(error);
    };
  });
}

// Usage
try {
  const result = await conductResearch("Why is Nvidia stock going up?");
  console.log("Report:", result.report);
  console.log("Sources:", result.metadata.sources);
} catch (error) {
  console.error("Research failed:", error);
}
```

### Python Example (Client)

```python
import asyncio
import websockets
import json

async def conduct_research(query: str):
    uri = "ws://localhost:8000/ws"

    async with websockets.connect(uri) as websocket:
        # Send research request
        request = {
            "task": query,
            "report_type": "research_report",
            "report_source": "web",
            "tone": "Objective",
            "verbose": True
        }
        await websocket.send(json.dumps(request))

        # Receive messages
        final_report = None
        async for message in websocket:
            data = json.loads(message)

            if data['type'] == 'logs':
                print(f"📊 {data['content']}")
            elif data['type'] == 'path':
                print(f"🔍 {data['content']}")
            elif data['type'] == 'report':
                print("✅ Research complete!")
                final_report = data
                break
            elif data['type'] == 'error':
                print(f"❌ {data['content']}")
                raise Exception(data['content'])

        return final_report

# Usage
result = asyncio.run(conduct_research("Why is Nvidia stock going up?"))
print(result['content'])
```

---

## Rate Limits & Performance

- **Deep Research Mode:** ~5 minutes per query, costs ~$0.40 with `o3-mini`
- **Standard Research:** ~2-3 minutes per query
- **Parallel Operations:** Controlled by `DEEP_RESEARCH_CONCURRENCY`
- **Token Limits:** Depends on LLM provider (OpenAI, Anthropic, etc.)

---

## Error Handling

Common error types:

| Error Code            | Description                | Resolution                                |
| --------------------- | -------------------------- | ----------------------------------------- |
| `RATE_LIMIT_EXCEEDED` | API rate limit hit         | Wait for `retry_after` seconds            |
| `INVALID_API_KEY`     | Missing/invalid API keys   | Check environment variables               |
| `CONNECTION_ERROR`    | Network/search API failure | Retry or check connectivity               |
| `TIMEOUT`             | Research took too long     | Reduce `MAX_ITERATIONS` or use faster LLM |

---

## Docker Deployment

```bash
# Using docker-compose (recommended)
docker-compose up --build

# Access at
# Backend: http://localhost:8000
# Frontend: http://localhost:3000 (if enabled)
```

---

## Notes

- **WebSocket is the primary interface** - REST endpoints are minimal
- **Stateless operation** - each WebSocket connection is independent
- **No built-in queue** - multiple concurrent requests execute in parallel (may overwhelm API limits)
- **Sources in metadata** - all cited sources returned with final report
- **Streaming is mandatory** - no synchronous API for complete reports

---

## Additional Resources

- **Official Docs:** https://docs.gptr.dev
- **GitHub:** https://github.com/assafelovic/gpt-researcher
- **NPM Package:** `gpt-researcher` (WebSocket client)
- **PyPI Package:** `gpt-researcher` (Python library)
