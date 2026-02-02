"""
title: GPT Researcher Remote Pipe
author: Marc Meese & Claude
author_url: https://github.com/assafelovic/gpt-researcher
version: 3.0.0
requirements: aiohttp

Changelog v3.0.0:
- Complete rewrite with structured message handling
- Separate handlers for each message type
- Clean state management
- Type-specific logic (research_report vs deep)
- Improved error handling and logging
- Zero code redundancy
"""

import json
import traceback
import aiohttp
from typing import Optional, Dict, Any, Callable, Awaitable
from pydantic import BaseModel, Field


class ResearchState:
    """Manages research state and report accumulation"""

    def __init__(self):
        self.report_chunks = []
        self.status = "Initializing..."
        self.is_complete = False

    def add_report_chunk(self, chunk: str) -> None:
        """Accumulate report chunks (NEVER overwrite!)"""
        self.report_chunks.append(chunk)

    def get_full_report(self) -> str:
        """Return complete accumulated report"""
        return "".join(self.report_chunks)

    def update_status(self, status: str) -> None:
        """Update current status"""
        self.status = status

    def mark_complete(self) -> None:
        """Mark research as complete"""
        self.is_complete = True


class MessageHandler:
    """Handles different WebSocket message types"""

    def __init__(
        self,
        state: ResearchState,
        emitter: Callable[[Dict[str, Any]], Awaitable[None]],
        verbose: bool = False,
    ):
        self.state = state
        self.emitter = emitter
        self.verbose = verbose

    async def handle_logs(self, content: str, output: str) -> None:
        """Handle log messages - update status"""
        status_text = output if output else content
        if not status_text:
            return

        # Clean up status text
        status_text = status_text.replace("✅", "").replace("🔍", "").strip()

        # Update state
        self.state.update_status(status_text)

        # Emit to UI
        await self.emitter(
            {
                "type": "status",
                "data": {
                    "description": status_text[:100]
                    + ("..." if len(status_text) > 100 else ""),
                    "done": False,
                },
            }
        )

        if self.verbose:
            print(f"[LOG] {status_text}")

    async def handle_report(self, output: str) -> None:
        """Handle report chunks - accumulate them"""
        if not output:
            return

        self.state.add_report_chunk(output)

        if self.verbose:
            print(
                f"[REPORT CHUNK] +{len(output)} chars (total: {len(self.state.get_full_report())})"
            )

    async def handle_path(self, output: Dict[str, Any]) -> bool:
        """
        Handle PATH messages - distinguish between sub-paths and final paths

        Returns:
            True if this is the final path (should end research)
            False if this is a sub-path (continue research)
        """
        if not isinstance(output, dict):
            return False

        # Check if this is the final report paths
        if any(key in output for key in ["pdf", "docx", "md", "json"]):
            # Final paths received - research complete!
            self.state.mark_complete()
            await self.emitter(
                {
                    "type": "status",
                    "data": {"description": "Research completed!", "done": True},
                }
            )

            if self.verbose:
                print(
                    f"[FINAL PATHS] Research complete. Report size: {len(self.state.get_full_report())} chars"
                )

            return True  # Signal to end loop

        # Check if this is a Deep Research sub-path
        if "query" in output:
            query = output.get("query", "Exploring...")
            await self.emitter(
                {
                    "type": "status",
                    "data": {
                        "description": f"Deep Research: {query[:80]}...",
                        "done": False,
                    },
                }
            )

            if self.verbose:
                print(f"[DEEP SUBQUERY] {query}")

            return False  # Continue research

        # Unknown path format - log warning but continue
        if self.verbose:
            print(f"[WARNING] Unknown PATH format: {output}")

        return False

    async def handle_message(self, msg_data: Dict[str, Any]) -> bool:
        """
        Process a single WebSocket message

        Returns:
            True if research should end, False to continue
        """
        msg_type = msg_data.get("type")

        if msg_type == "logs":
            await self.handle_logs(
                msg_data.get("content", ""), msg_data.get("output", "")
            )

        elif msg_type == "report":
            await self.handle_report(msg_data.get("output", ""))

        elif msg_type == "path":
            return await self.handle_path(msg_data.get("output", {}))

        return False  # Continue by default


class Pipe:
    """GPT Researcher Remote Client for OpenWebUI"""

    class Valves(BaseModel):
        # Connection
        GPT_RESEARCHER_WS_URL: str = Field(
            default="ws://gptresearcher-server:8000/ws",
            description="WebSocket URL of GPT Researcher container",
        )

        # Research Type
        REPORT_TYPE: str = Field(
            default="research_report",
            description="Report type: 'research_report', 'deep', 'resource_report', 'outline_report'",
        )
        REPORT_SOURCE: str = Field(
            default="web", description="Source: 'web', 'local', 'hybrid'"
        )
        TONE: str = Field(default="Objective", description="Report tone")

        # Deep Research (only used if REPORT_TYPE="deep")
        DEEP_RESEARCH_BREADTH: int = Field(
            default=4, description="[Deep only] Parallel research paths"
        )
        DEEP_RESEARCH_DEPTH: int = Field(
            default=2, description="[Deep only] Research depth"
        )

        # General Settings
        TOTAL_WORDS: int = Field(default=2500, description="Target word count")
        VERBOSE: bool = Field(default=False, description="Enable verbose logging")

    def __init__(self):
        self.valves = self.Valves()

    def _build_request_config(self, query: str) -> Dict[str, Any]:
        """Build request config based on report type"""
        config = {
            "task": query,
            "report_type": self.valves.REPORT_TYPE,
            "report_source": self.valves.REPORT_SOURCE,
            "source_urls": [],
            "tone": self.valves.TONE,
            "agent": "Auto Agent",
            "total_words": self.valves.TOTAL_WORDS,
        }

        # Only add Deep Research params for deep mode
        if self.valves.REPORT_TYPE == "deep":
            config["deep_research_breadth"] = self.valves.DEEP_RESEARCH_BREADTH
            config["deep_research_depth"] = self.valves.DEEP_RESEARCH_DEPTH

            if self.valves.VERBOSE:
                print(
                    f"[DEEP MODE] breadth={config['deep_research_breadth']}, depth={config['deep_research_depth']}"
                )

        return config

    async def _handle_websocket_stream(
        self, ws: aiohttp.ClientWebSocketResponse, handler: MessageHandler
    ) -> None:
        """Process WebSocket stream until completion"""
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = msg.data

                # Handle keepalive ping/pong
                if data == "ping":
                    await ws.send_str("pong")
                    if self.valves.VERBOSE:
                        print("[KEEPALIVE] pong")
                    continue

                # Parse JSON messages
                if data.startswith('{"type":'):
                    try:
                        msg_data = json.loads(data)
                        should_end = await handler.handle_message(msg_data)

                        if should_end:
                            break  # Research complete

                    except json.JSONDecodeError as e:
                        if self.valves.VERBOSE:
                            print(f"[JSON ERROR] {e}")
                        continue

            elif msg.type == aiohttp.WSMsgType.ERROR:
                print(f"[WS ERROR] {ws.exception()}")
                break

            elif msg.type == aiohttp.WSMsgType.CLOSE:
                if self.valves.VERBOSE:
                    print("[WS CLOSED]")
                break

    async def pipe(
        self, body: dict, __user__: dict = None, __event_emitter__=None
    ) -> str:
        """
        Main entry point - conduct research and return report
        """

        # Setup emitter (dummy if not provided)
        async def dummy_emitter(*args, **kwargs):
            pass

        emitter = __event_emitter__ if __event_emitter__ else dummy_emitter

        # Extract query
        query = body.get("messages", [{}])[-1].get("content", None)
        if not query:
            return "❌ Error: No query provided"

        # Initialize state
        state = ResearchState()
        handler = MessageHandler(state, emitter, self.valves.VERBOSE)

        try:
            await emitter(
                {
                    "type": "status",
                    "data": {
                        "description": "Connecting to Research Engine...",
                        "done": False,
                    },
                }
            )

            # Prepare request
            request_config = self._build_request_config(query)

            # Configure timeout (no read timeout for long deep research)
            timeout = aiohttp.ClientTimeout(
                total=None, connect=60, sock_connect=60, sock_read=None
            )

            # Connect and stream
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.ws_connect(
                    self.valves.GPT_RESEARCHER_WS_URL, heartbeat=30
                ) as ws:

                    # Send start command
                    start_msg = f"start {json.dumps(request_config)}"
                    await ws.send_str(start_msg)

                    if self.valves.VERBOSE:
                        print(f"[SENT] {start_msg[:100]}...")

                    # Process stream
                    await self._handle_websocket_stream(ws, handler)

            # Return accumulated report
            report = state.get_full_report()

            if report:
                if self.valves.VERBOSE:
                    print(f"[SUCCESS] Report size: {len(report)} chars")

                await emitter(
                    {
                        "type": "status",
                        "data": {"description": "Research completed!", "done": True},
                    }
                )

                return report
            else:
                return "⚠️ Research completed but no report was generated. Check server logs."

        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            traceback.print_exc()

            # If we captured partial report before error, return it
            report = state.get_full_report()
            if report:
                return f"{report}\n\n---\n⚠️ Connection interrupted but partial report recovered."

            await emitter(
                {"type": "status", "data": {"description": error_msg, "done": True}}
            )

            return error_msg
