# GPT-Researcher API Documentation

**Version:** 0.14.5  
**Base URL:** `http://localhost:8000` (default)  
**Protocol:** FastAPI with WebSocket support

---

## Overview

GPT-Researcher exposes a FastAPI-based backend that supports WebSocket connections for real-time research streaming. The primary communication method is via WebSocket at `/ws`.

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

**IMPORTANT:** The message format is **NOT** plain JSON. It must be a string with the prefix `start ` followed by JSON data.

**Format:**

```
start {"task":"...","report_type":"...","report_source":"...","tone":"...","query_domains":[],"mcp_enabled":false,"mcp_strategy":"fast","mcp_configs":[]}
```

**Example:**

```javascript
const dataToSend = {
  task: "Why is Nvidia stock going up?",
  report_type: "research_report",
  report_source: "web",
  tone: "Objective",
  query_domains: [],
  mcp_enabled: false,
  mcp_strategy: "fast",
  mcp_configs: [],
};

const message = `start ${JSON.stringify(dataToSend)}`;
socket.send(message);
```

**Parameters:**

| Parameter       | Type    | Required | Default             | Description                                                                                                                                                                                                                                                    |
| --------------- | ------- | -------- | ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `task`          | string  | Yes      | -                   | The research query/question                                                                                                                                                                                                                                    |
| `report_type`   | string  | No       | `"research_report"` | Type of report (see Report Types below)                                                                                                                                                                                                                        |
| `report_source` | string  | No       | `"web"`             | Source for research: `"web"`, `"local"`, `"hybrid"`                                                                                                                                                                                                            |
| `tone`          | string  | No       | `"Objective"`       | Tone of the report: `"Objective"`, `"Formal"`, `"Analytical"`, `"Persuasive"`, `"Informative"`, `"Explanatory"`, `"Descriptive"`, `"Critical"`, `"Comparative"`, `"Speculative"`, `"Reflective"`, `"Narrative"`, `"Humorous"`, `"Optimistic"`, `"Pessimistic"` |
| `query_domains` | array   | No       | `[]`                | List of specific domains to search (domain filtering)                                                                                                                                                                                                          |
| `mcp_enabled`   | boolean | No       | `false`             | Enable Model Context Protocol integration                                                                                                                                                                                                                      |
| `mcp_strategy`  | string  | No       | `"fast"`            | MCP strategy: `"fast"` or `"comprehensive"`                                                                                                                                                                                                                    |
| `mcp_configs`   | array   | No       | `[]`                | MCP configuration objects                                                                                                                                                                                                                                      |

#### Report Types

- `"research_report"` - Standard comprehensive research report
- `"detailed_report"` - More detailed analysis
- `"resource_report"` - Focus on gathering resources/sources
- `"outline_report"` - Structured outline format
- `"custom_report"` - Custom formatted report
- `"deep"` - Deep recursive research (5+ minutes, experimental)

#### Message Format (Server → Client)

The server streams multiple message types during research. All messages are JSON objects.

##### 1. Logs (Research Progress)

```json
{
  "type": "logs",
  "content": "starting_research",
  "output": "🔍 Starting the research task for 'Why is Nvidia stock going up?'",
  "metadata": null
}
```

**Common log content types:**

- `"starting_research"` - Research initiated
- `"agent_generated"` - Agent type selected
- `"planning_research"` - Planning phase
- `"subqueries"` - Research questions generated
- `"running_subquery_research"` - Processing sub-questions
- `"researching"` - Active research
- `"scraping_urls"` - Web scraping in progress
- `"scraping_content"` - Content extraction
- `"scraping_images"` - Image collection
- `"scraping_complete"` - Scraping finished
- `"subquery_context_not_found"` - No content found for query
- `"research_step_finalized"` - Research phase complete
- `"image_planning"` - Image generation planning
- `"image_concepts_identified"` - Images to generate identified
- `"image_generating"` - Generating image
- `"images_failed"` - Image generation failed
- `"writing_report"` - Composing final report
- `"report_written"` - Report complete

##### 2. Report (Streaming Content)

The report is sent in **chunks**, not as a single message. Each chunk contains a portion of the markdown report.

```json
{
  "type": "report",
  "output": "# Research Report: Why is Nvidia Stock Going Up?\n\n"
}
```

```json
{
  "type": "report",
  "output": "## Introduction\n\n"
}
```

```json
{
  "type": "report",
  "output": "Nvidia Corporation has experienced significant stock growth..."
}
```

**Note:** The client must concatenate all `report` chunks to build the complete report.

##### 3. Path (Report File Paths)

Sent at the end of research with file paths to saved reports.

```json
{
  "type": "path",
  "output": {
    "pdf": "",
    "docx": "outputs/task_1769951557_bec4b06e03.docx",
    "md": "outputs/task_1769951557_bec4b06e03.md",
    "json": "outputs/task_1769951557_bec4b06e03.json"
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

##### 5. Ping/Pong (Keepalive)

The server may send `"ping"` messages every 30 seconds. Clients should respond with `"pong"`.

```javascript
socket.onmessage = (event) => {
  if (event.data === "ping") {
    socket.send("pong");
    return;
  }
  // ... handle JSON messages
};
```

---

### 2. Health Check Endpoint

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

### Image Generation (Optional)

```bash
# Enable inline images in reports
IMAGE_GENERATION_ENABLED=false
IMAGE_GENERATION_MODEL=gemini-2.0-flash-preview-image-generation
IMAGE_GENERATION_MAX_IMAGES=3
GOOGLE_API_KEY=...  # Required for Gemini image generation
```

---

## Status Message Types Reference

During WebSocket streaming, the server sends different message types:

| Type     | Purpose                     | Field with Content | Frequency      |
| -------- | --------------------------- | ------------------ | -------------- |
| `logs`   | Research progress updates   | `output`           | Continuous     |
| `report` | Report content (streaming)  | `output`           | Multiple times |
| `path`   | File paths to saved reports | `output`           | Once (at end)  |
| `error`  | Error information           | `content`          | On error       |

---

## Example: Complete Research Flow

### JavaScript/TypeScript Example (Official UI Format)

```javascript
async function conductResearch(query) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket("ws://localhost:8000/ws");
    let fullReport = "";
    const logs = [];

    socket.onopen = () => {
      // Prepare request data
      const dataToSend = {
        task: query,
        report_type: "research_report",
        report_source: "web",
        tone: "Objective",
        query_domains: [],
        mcp_enabled: false,
        mcp_strategy: "fast",
        mcp_configs: [],
      };

      // CRITICAL: Must use "start " prefix
      const message = `start ${JSON.stringify(dataToSend)}`;
      socket.send(message);
    };

    socket.onmessage = (event) => {
      // Handle ping/pong
      if (event.data === "pong") return;

      try {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case "logs":
            console.log("📊", data.output);
            logs.push(data.output);
            break;

          case "report":
            // Accumulate report chunks
            fullReport += data.output;
            break;

          case "path":
            console.log("✅ Research complete!");
            console.log("Report files:", data.output);
            socket.close();
            break;

          case "error":
            console.error("❌", data.content);
            reject(new Error(data.content));
            break;
        }
      } catch (error) {
        console.error("Error parsing message:", error);
      }
    };

    socket.onclose = () => {
      if (fullReport) {
        resolve({
          report: fullReport,
          logs: logs,
        });
      } else {
        reject(new Error("Connection closed without report"));
      }
    };

    socket.onerror = (error) => {
      reject(error);
    };

    // Send pong in response to ping
    setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send("pong");
      }
    }, 30000);
  });
}

// Usage
try {
  const result = await conductResearch("Why is Nvidia stock going up?");
  console.log("Report:", result.report);
  console.log("Total log entries:", result.logs.length);
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
    full_report = ""
    logs = []

    async with websockets.connect(uri) as websocket:
        # Prepare request
        request_data = {
            "task": query,
            "report_type": "research_report",
            "report_source": "web",
            "tone": "Objective",
            "query_domains": [],
            "mcp_enabled": False,
            "mcp_strategy": "fast",
            "mcp_configs": []
        }

        # CRITICAL: Must use "start " prefix
        message = f"start {json.dumps(request_data)}"
        await websocket.send(message)

        # Receive messages
        async for message in websocket:
            # Handle ping/pong
            if message == "ping":
                await websocket.send("pong")
                continue

            try:
                data = json.loads(message)

                if data['type'] == 'logs':
                    print(f"📊 {data['output']}")
                    logs.append(data['output'])

                elif data['type'] == 'report':
                    # Accumulate report chunks
                    full_report += data['output']

                elif data['type'] == 'path':
                    print("✅ Research complete!")
                    print(f"Report files: {data['output']}")
                    break

                elif data['type'] == 'error':
                    print(f"❌ {data['content']}")
                    raise Exception(data['content'])

            except json.JSONDecodeError as e:
                print(f"Error parsing message: {e}")

        return {
            "report": full_report,
            "logs": logs
        }

# Usage
result = asyncio.run(conduct_research("Why is Nvidia stock going up?"))
print("=== FINAL REPORT ===")
print(result['report'])
print(f"\n=== STATISTICS ===")
print(f"Total log entries: {len(result['logs'])}")
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

| Error Code                                          | Description                | Resolution                                 |
| --------------------------------------------------- | -------------------------- | ------------------------------------------ |
| `RATE_LIMIT_EXCEEDED`                               | API rate limit hit         | Wait for `retry_after` seconds             |
| `INVALID_API_KEY`                                   | Missing/invalid API keys   | Check environment variables                |
| `CONNECTION_ERROR`                                  | Network/search API failure | Retry or check connectivity                |
| `TIMEOUT`                                           | Research took too long     | Reduce `MAX_ITERATIONS` or use faster LLM  |
| `Unknown command or not enough parameters provided` | Invalid message format     | Ensure message starts with `start ` prefix |

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

## Critical Implementation Notes

### ⚠️ Message Format

**The most common integration error** is sending plain JSON instead of the `start` prefix format.

**WRONG:**

```javascript
socket.send(JSON.stringify({ task: "...", report_type: "..." }));
```

**CORRECT:**

```javascript
const message = `start ${JSON.stringify({ task: "...", report_type: "..." })}`;
socket.send(message);
```

### ⚠️ Report Accumulation

Reports are sent as **multiple chunks**, not a single message. You must concatenate them:

```javascript
let fullReport = "";

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === "report") {
    fullReport += data.output; // Accumulate chunks
  }
};
```

### ⚠️ Field Names

Server messages use **`output`** for most content, not `content`:

```json
{
  "type": "logs",
  "output": "🔍 Starting research...", // <-- output, not content
  "content": "starting_research" // <-- content is the type identifier
}
```

Exception: Error messages use `content` for the error description.

---

## Notes

- **WebSocket is the only interface** - no REST API for research requests
- **Stateless operation** - each WebSocket connection is independent
- **No built-in queue** - multiple concurrent requests execute in parallel (may overwhelm API limits)
- **Streaming is mandatory** - no synchronous API for complete reports
- **Message format is critical** - must use `start ` prefix or server will reject with "Unknown command"

---

## Additional Resources

- **Official Docs:** https://docs.gptr.dev
- **GitHub:** https://github.com/assafelovic/gpt-researcher
- **NPM Package:** `gpt-researcher` (WebSocket client)
- **PyPI Package:** `gpt-researcher` (Python library)
- **Frontend Source:** https://github.com/assafelovic/gpt-researcher/tree/master/frontend/nextjs

---

## Changelog

**Updated 2025-02-01:**

- Corrected message format to include `start ` prefix requirement
- Updated field list to match actual implementation (removed `source_urls`, `headers`, `verbose`)
- Added correct fields: `query_domains`, `mcp_enabled`, `mcp_strategy`, `mcp_configs`
- Clarified that server uses `output` field, not `content` for most messages
- Added report chunking/accumulation documentation
- Added ping/pong keepalive documentation
- Included common error: "Unknown command or not enough parameters provided"
