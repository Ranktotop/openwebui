"""
GPT-Researcher Queue Server
A middleware that queues research requests and proxies status updates.
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel

LOG_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
GPTRESEARCHER_WS_URL = os.environ["GPTRESEARCHER_WS_URL"]  # GPT-Researcher WebSocket
MAX_CONCURRENT_RESEARCH = int(os.environ.get("MAX_CONCURRENT_RESEARCH", 1))  # Maximum parallel research tasks


class ResearchRequest(BaseModel):
    """Research request model"""
    task: str
    report_type: str = "research_report"
    report_source: str = "web"
    source_urls: list = []
    tone: str = "Objective"
    query_domains: list = []      # NEU
    mcp_enabled: bool = False      # NEU
    mcp_strategy: str = "fast"     # NEU
    mcp_configs: list = []         # NEU
    headers: dict = {}
    verbose: bool = True


class QueueManager:
    """Manages research request queue and processing"""

    def __init__(self, max_concurrent: int = MAX_CONCURRENT_RESEARCH):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.active_tasks: int = 0
        self.max_concurrent = max_concurrent
        self.worker_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the queue worker"""
        if self.worker_task is None:
            self.worker_task = asyncio.create_task(self._worker())
            logger.info("Queue worker started")

    async def stop(self):
        """Stop the queue worker"""
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            logger.info("Queue worker stopped")

    async def add_request(self, request: Dict[str, Any], client_ws: WebSocket) -> int:
        """
        Add a research request to the queue
        Returns: Position in queue (0 = processing now, 1+ = waiting)
        """
        position = self.queue.qsize()
        await self.queue.put((request, client_ws))
        logger.info(f"Request added to queue. Position: {position}, Active: {self.active_tasks}")
        return position

    async def _worker(self):
        """Worker that processes queued research requests"""
        logger.info("Queue worker running")

        while True:
            try:
                # Wait for a request
                request, client_ws = await self.queue.get()

                # Wait until we have capacity
                while self.active_tasks >= self.max_concurrent:
                    logger.info(f"Max concurrent reached ({self.max_concurrent}). Waiting...")
                    await asyncio.sleep(1)

                # Process the request
                self.active_tasks += 1
                logger.info(f"Processing request. Active: {self.active_tasks}/{self.max_concurrent}")

                try:
                    await self._process_research(request, client_ws)
                except Exception as e:
                    logger.error(f"Error processing research: {e}", exc_info=True)
                    await self._send_error(client_ws, str(e))
                finally:
                    self.active_tasks -= 1
                    self.queue.task_done()
                    logger.info(f"Request completed. Active: {self.active_tasks}/{self.max_concurrent}")

            except asyncio.CancelledError:
                logger.info("Worker cancelled")
                break
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)

    async def _process_research(self, request: Dict[str, Any], client_ws: WebSocket):
        """
        Process a research request by connecting to GPT-Researcher
        and proxying messages back to the client
        """
        logger.info(f"Connecting to GPT-Researcher: {GPTRESEARCHER_WS_URL}")

        try:
            async with websockets.connect(GPTRESEARCHER_WS_URL) as gptr_ws:
                # Send research request to GPT-Researcher
                message = f"start {json.dumps(request)}"
                await gptr_ws.send(message)
                logger.info("Research request sent to GPT-Researcher")

                # Proxy messages from GPT-Researcher to client
                async for message in gptr_ws:
                    try:
                        data = json.loads(message)

                        # Forward message to client
                        await client_ws.send_json(data)

                        # Check if research is complete
                        if data.get('type') == 'report':
                            logger.info("Research completed successfully")
                            break
                        elif data.get('type') == 'error':
                            logger.error(f"Research error: {data.get('content')}")
                            break

                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON from GPT-Researcher: {e}")
                    except Exception as e:
                        logger.error(f"Error forwarding message: {e}")

        except websockets.exceptions.WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            await self._send_error(client_ws, f"Connection to GPT-Researcher failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            await self._send_error(client_ws, f"Internal error: {str(e)}")

    async def _send_error(self, client_ws: WebSocket, error_msg: str):
        """Send error message to client"""
        try:
            await client_ws.send_json({
                "type": "error",
                "content": error_msg,
                "metadata": {
                    "timestamp": datetime.now().isoformat()
                }
            })
        except Exception as e:
            logger.error(f"Failed to send error to client: {e}")

    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()

    def get_active_tasks(self) -> int:
        """Get number of active research tasks"""
        return self.active_tasks


# Global queue manager
queue_manager = QueueManager(max_concurrent=MAX_CONCURRENT_RESEARCH)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Queue Server...")
    await queue_manager.start()
    yield
    # Shutdown
    logger.info("Shutting down Queue Server...")
    await queue_manager.stop()


# FastAPI app
app = FastAPI(
    title="GPT-Researcher Queue Server",
    description="Middleware for queuing and managing GPT-Researcher requests",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "ok",
        "service": "gpt-researcher-queue-server",
        "version": os.getenv("VERSION", "unknown"),
        "queue_size": queue_manager.get_queue_size(),
        "active_tasks": queue_manager.get_active_tasks(),
        "max_concurrent": queue_manager.max_concurrent
    })


@app.get("/status")
async def get_status():
    """Get queue status"""
    return JSONResponse({
        "queue_size": queue_manager.get_queue_size(),
        "active_tasks": queue_manager.get_active_tasks(),
        "max_concurrent": queue_manager.max_concurrent,
        "available_slots": queue_manager.max_concurrent - queue_manager.get_active_tasks()
    })


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for research requests
    Accepts requests from OpenWebUI and proxies to GPT-Researcher
    """
    await websocket.accept()
    client_id = id(websocket)
    logger.info(f"Client connected: {client_id}")

    try:
        # Wait for research request
        data = await websocket.receive_text()
        request = json.loads(data)

        logger.info(f"Received request from client {client_id}: {request.get('task', 'Unknown')[:50]}...")

        # Check queue position
        position = queue_manager.get_queue_size()

        if position >= queue_manager.max_concurrent:
            # Send waiting status
            queue_position = position + 1
            await websocket.send_json({
                "type": "logs",
                "content": f"⏳ Waiting for available research slot... Position in queue: {queue_position}",
                "metadata": {
                    "status": "waiting",
                    "queue_position": queue_position,
                    "timestamp": datetime.now().isoformat()
                }
            })
            logger.info(f"Client {client_id} waiting in queue at position {queue_position}")

        # Add to queue (worker will process when slot is available)
        await queue_manager.add_request(request, websocket)

        # Send queue accepted confirmation
        await websocket.send_json({
            "type": "logs",
            "content": "✅ Request queued successfully. Research will start shortly...",
            "metadata": {
                "status": "queued",
                "timestamp": datetime.now().isoformat()
            }
        })

        # Keep connection alive until research completes or client disconnects
        # The queue worker will send messages through this websocket
        try:
            while True:
                # Just wait for client to disconnect or send ping/pong
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            logger.info(f"Client {client_id} disconnected")

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected during setup")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from client {client_id}: {e}")
        await websocket.send_json({
            "type": "error",
            "content": "Invalid JSON format",
            "metadata": {"timestamp": datetime.now().isoformat()}
        })
    except Exception as e:
        logger.error(f"Error handling client {client_id}: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"Server error: {str(e)}",
                "metadata": {"timestamp": datetime.now().isoformat()}
            })
        except:
            pass
    finally:
        logger.info(f"Client {client_id} connection closed")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "service:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
        reload=False
    )
