"""
title: GPT Researcher Remote Pipe (Robust)
author: Marc Meese & Gemini
author_url: https://github.com/assafelovic/gpt-researcher
version: 2.1.0
requirements: aiohttp
"""

import os
import json
import traceback
import aiohttp
from pydantic import BaseModel, Field
from typing import Optional

class Pipe:
    """
    A Remote Client Pipe for the GPT Researcher Docker Container.
    Connects via WebSocket to the backend, streams progress, and returns the markdown report.
    Robust against connection drops after report generation.
    """

    class Valves(BaseModel):
        # --- Connection Configuration ---
        GPT_RESEARCHER_WS_URL: str = Field(
            default="ws://gptresearcher-server:8000/ws",
            description="WebSocket URL of the GPT Researcher Container (internal docker name).",
        )

        # --- Research Parameters ---
        REPORT_TYPE: str = Field(
            default="deep",
            description="Type of report ('deep', 'research_report', 'resource_report', 'outline_report').",
        )
        REPORT_SOURCE: str = Field(
            default="web",
            description="Source of information ('web', 'local').",
        )
        TONE: str = Field(
            default="Objective",
            description="Tone of the report (e.g., 'Objective', 'Critical', 'Funny').",
        )
        
        # --- Deep Research Params ---
        DEEP_RESEARCH_BREADTH: int = Field(
            default=4,
            description="[Deep only] Breadth of research (parallel paths).",
        )
        DEEP_RESEARCH_DEPTH: int = Field(
            default=2,
            description="[Deep only] Depth of research (recursion levels).",
        )
        
        # --- Limits ---
        TOTAL_WORDS: int = Field(
            default=2500,
            description="Target word count.",
        )
        
        VERBOSE: bool = Field(
            default=False,
            description="Log all WebSocket messages to console.",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def pipe(self, body: dict, __user__: dict = None, __event_emitter__=None):
        print(f"GPT Researcher Remote Pipe called.")

        # 1. Setup Emitter
        async def dummy_emitter(*args, **kwargs):
            pass
        _emitter = __event_emitter__ if __event_emitter__ else dummy_emitter

        # 2. Extract Query
        query = body.get("messages", [{}])[-1].get("content", None)
        if not query:
            return "Error: No query provided."

        # 3. Prepare Payload
        request_config = {
            "task": query,
            "report_type": self.valves.REPORT_TYPE,
            "report_source": self.valves.REPORT_SOURCE,
            "source_urls": [], 
            "tone": self.valves.TONE,
            "agent": "Auto Agent", 
            "deep_research_breadth": self.valves.DEEP_RESEARCH_BREADTH,
            "deep_research_depth": self.valves.DEEP_RESEARCH_DEPTH,
            "total_words": self.valves.TOTAL_WORDS
        }

        final_report = ""
        
        try:
            await _emitter({"type": "status", "data": {"description": "Connecting to Research Engine...", "done": False}})
            
            # Timeout Settings: Deep Research takes time. We disable read timeout mostly.
            timeout = aiohttp.ClientTimeout(total=None, connect=60, sock_connect=60, sock_read=None)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Heartbeat is important to keep connection alive during long silent thinking
                async with session.ws_connect(self.valves.GPT_RESEARCHER_WS_URL, heartbeat=30) as ws:
                    
                    print(f"Sending request to {self.valves.GPT_RESEARCHER_WS_URL}...")
                    await ws.send_str(f"start {json.dumps(request_config)}")

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = msg.data
                            
                            if data.startswith('{"type":'):
                                try:
                                    json_data = json.loads(data)
                                    msg_type = json_data.get("type")
                                    content = json_data.get("content", "")
                                    output = json_data.get("output", "")
                                    
                                    # --- LOGS handling ---
                                    if msg_type == "logs":
                                        log_text = output if output else content
                                        if log_text:
                                            log_text = log_text.replace("✅", "").strip()
                                            
                                            # Special handling for "Report written" message
                                            if "Report written" in log_text:
                                                await _emitter({"type": "status", "data": {"description": "Report finalized. Receiving data...", "done": False}})

                                            # Emit status update
                                            await _emitter({
                                                "type": "status",
                                                "data": {
                                                    "description": f"{log_text[:80]}...",
                                                    "done": False
                                                }
                                            })
                                            if self.valves.VERBOSE:
                                                print(f"[WS LOG] {log_text}")

                                    # --- REPORT handling ---
                                    elif msg_type == "report":
                                        # Whenever we get a report chunk or full report, save it.
                                        # Usually 'output' contains the markdown.
                                        if output:
                                            final_report = output
                                            print("Report received in stream.")
                                    
                                    # --- PATH handling (Deep Research) ---
                                    elif msg_type == "path":
                                        path_info = output
                                        await _emitter({
                                            "type": "status",
                                            "data": {
                                                "description": f"Deep Dive: {path_info.get('query', 'Exploring...')}",
                                                "done": False
                                            }
                                        })

                                except json.JSONDecodeError:
                                    pass
                            
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            print('WebSocket connection closed with error:', ws.exception())
                            break
                        elif msg.type == aiohttp.WSMsgType.CLOSE:
                            print('WebSocket connection closed normally.')
                            break

            # --- FINALIZE ---
            # If the connection closed (even with error) but we have the report, return it!
            if final_report:
                await _emitter({"type": "status", "data": {"description": "Research Completed.", "done": True}})
                return final_report
            
            return "Error: Research finished but no report data was captured. Check container logs."

        except Exception as e:
            traceback.print_exc()
            # Emergency Recovery: If we captured the report before the crash, return it
            if final_report:
                return final_report
                
            await _emitter({"type": "status", "data": {"description": f"Error: {str(e)}", "done": True}})
            return f"Connection Error: {str(e)}"