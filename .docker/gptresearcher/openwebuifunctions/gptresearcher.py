"""
title: GPT Researcher Remote Pipe
author: Marc Meese & Claude
author_url: https://github.com/assafelovic/gpt-researcher
version: 4.0.0
requirements: aiohttp

Changelog v4.0.0:
- Interactive research workflow with type selection
- Default model integration for classification and follow-ups
- Comprehensive logging
"""
import asyncio
import json
import traceback
import aiohttp
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Awaitable, List, Union
from pydantic import BaseModel, Field
from datetime import datetime
from fastapi import Request
from open_webui.models.users import Users
from open_webui.utils.chat import generate_chat_completion
import base64

###########################
######### STATE ###########
###########################


class ResearchState:
    """Manages research state and report accumulation"""

    def __init__(self):
        """Constructor for ResearchState"""
        self.report_chunks = []
        self.status = "Initializing..."
        self.is_complete = False

    def add_report_chunk(self, chunk: str) -> None:
        """Add a chunk to the report"""
        self.report_chunks.append(chunk)

    def get_full_report(self) -> str:
        """
        Concatenate all report chunks into a full report

        Returns:
            str: Full report as a single string
        """
        return "".join(self.report_chunks)

    def update_status(self, status: str) -> None:
        """Update the current status of the research"""
        self.status = status

    def mark_complete(self) -> None:
        """Mark the research as complete"""
        self.is_complete = True

###########################
######### HELPER ##########
###########################


class Logger:

    def __init__(self, verbose: bool = False):
        """Constructor for Logger"""
        self.verbose = verbose

    def log(self, msg: Any, prefix: str = "", section_divider: bool = False) -> None:
        """
        Robust logging function with multiple fallback strategies

        Args:
            msg (Any): Message to log
            prefix (str): Prefix for the log message
            section_divider (bool): If True, print a divider before the message

        Returns:
            None
        """
        # do not print if not verbose
        if not self.verbose:
            return

        if isinstance(msg, str):
            final_msg = msg
        else:
            final_msg = None

            if isinstance(msg, datetime):
                try:
                    final_msg = msg.isoformat()
                except Exception:
                    pass

            # Strategy 1: JSON serialization
            if final_msg is None:
                try:
                    final_msg = json.dumps(msg, ensure_ascii=False, default=str)
                except (TypeError, ValueError, OverflowError):
                    pass

            # Strategy 2: repr()
            if final_msg is None:
                try:
                    final_msg = repr(msg)
                except Exception:
                    pass

            # Strategy 3: __dict__
            if final_msg is None:
                try:
                    if hasattr(msg, '__dict__'):
                        final_msg = json.dumps(msg.__dict__, ensure_ascii=False, default=str)
                except Exception:
                    pass

            # Strategy 4: str()
            if final_msg is None:
                try:
                    final_msg = str(msg)
                except Exception:
                    pass

            # Strategy 5: type info
            if final_msg is None:
                try:
                    final_msg = f"<{type(msg).__name__} object at {hex(id(msg))}>"
                except Exception:
                    pass

            # Last resort
            if final_msg is None:
                final_msg = "<unprintable message>"

        # Print with section divider if requested
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if section_divider:
            print("\n" + "=" * 60)

        try:
            print(f"[{timestamp}][{prefix}]->{final_msg}")
        except UnicodeEncodeError:
            safe_msg = final_msg.encode('utf-8', errors='replace').decode('utf-8')
            print(f"[{timestamp}][{prefix}]->{safe_msg}")
        except Exception as e:
            print(f"[{timestamp}][{prefix}]-><logging error: {type(e).__name__}>")

###########################
######### Models ##########
###########################


class ModelCaller:
    def __init__(self, logger: Logger, model: str, user: dict = None, request: Request = None):
        """
        Constructor for ModelCaller

        Args:
            logger (Logger): Logger instance
            model (str): Model ID to call. E.g.: "llama3.2:latest"
            user (dict, optional): User information. Defaults to None.
            request (Request, optional): Request object. Defaults to None.
        """
        self.logger = logger
        self.model = model
        self.user = user
        self.request = request

    async def do_prompt(self, prompt: str = "", role: str = "user", messages: Optional[List[Dict[str, str]]] = None, **kwargs) -> str:
        """
        Prompt the model with either a prompt string and/or a list of messages

        Args:
            prompt (str): Prompt string to add as user message after existing messages
            role (str): Role of the prompt message. Defaults to "user".
            messages (List[Dict[str, str]], optional): List of message dicts
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            str: Model response

        Raises:
            ValueError: If no messages or prompt provided
            Exception: If user is not available
            Exception: If request is not available
        """
        if not self.user:
            raise Exception("user not available")
        if not self.request:
            raise Exception("request not available")

        if not messages:
            messages = []

        # add user prompt if provided
        if prompt.strip():
            if role == "system":
                # if this is a system prompt but there are no other messages, throw error
                if not messages:
                    raise ValueError("Cannot add system prompt without other messages")

                # create a new copy of list with system prompt at the start
                messages = [{"role": "system", "content": prompt.strip()}] + \
                    [msg for msg in messages if msg["role"] != "system"]
            else:
                # create a new copy of list with prompt at the end
                messages = [msg for msg in messages if msg["role"] != "system"] + [{"role": role, "content": prompt.strip()}]

        # if no messages after this, raise error
        if not messages:
            raise ValueError("No messages or prompt provided for model call")

        return await self._call(messages, **kwargs)

    async def _call(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Call another model via event_call

        Args:
            messages: List of message dicts
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            str: Model response

        Raises:
            Exception: If event_call fails
        """
        self.logger.log(f"Calling {self.model}", "ModelCaller")
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
            }
            # add additional kwargs
            payload.update(kwargs)
            result = await generate_chat_completion(self.request, payload, Users.get_user_by_id(self.user["id"]))
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            self.logger.log(f"Error: {e}", "ModelCaller")
            raise

##############################
######### WebSocket ##########
##############################


class MessageHandler:
    """Handles different WebSocket message types"""

    def __init__(self, state: ResearchState, logger: Logger, emitter: Callable[[Dict[str, Any]], Awaitable[None]], verbose: bool = False):
        """
        Constructor for MessageHandler
        Args:
            state (ResearchState): Research state instance
            logger (Logger): Logger instance
            emitter (Callable[[Dict[str, Any]], Awaitable[None]]): Event emitter function
            verbose (bool): Verbose logging flag
        """
        self.state = state
        self.emitter = emitter
        self.verbose = verbose
        self.logger = logger

    async def handle_logs(self, content: str, output: str, metadata: Any = None) -> None:
        """
        Handle log messages and update research state
        Args:
            content (str): Log content
            output (str): Additional output
            metadata (Any): Additional metadata, e.g. image URLs
        Returns:
            None
        """
        status_text = output if output else content
        if not status_text:
            return

        status_text = status_text.replace("✅", "").replace("🔍", "").strip()
        self.state.update_status(status_text)

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

        self.logger.log(f"[WS LOG] {status_text[:80]}", "MessageHandler")

        # NEW: Extract and emit images
        if content == "scraping_images" and metadata and isinstance(metadata, list):
            # metadata contains image URLs like:
            # ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]

            for img_url in metadata[:3]:  # Limit to first 3 images
                await self.emitter({
                    "type": "message",
                    "data": {
                        "content": f"![Research Image]({img_url})"
                    }
                })

            self.logger.log(f"Emitted {len(metadata[:3])} images", "MessageHandler")

    async def handle_report(self, output: str) -> None:
        """
        Handle report messages and add to research state

        Args:
            output (str): Report content to add

        Returns:
            None        
        """
        if not output:
            return
        self.state.add_report_chunk(output)
        self.logger.log(f"Added report chunk of {len(output)} chars", "MessageHandler")

    async def handle_path(self, output: Dict[str, Any]) -> bool:
        """
        Handle path messages and update research state accordingly

        Args:
            output (Dict[str, Any]): Output data from the path message

        Returns:
            bool: True if research is complete, False otherwise
        """
        if not isinstance(output, dict):
            return False

        if any(key in output for key in ["pdf", "docx", "md", "json"]):
            self.state.mark_complete()
            await self.emitter(
                {
                    "type": "status",
                    "data": {"description": "Research completed!", "done": True},
                }
            )
            self.logger.log(f"Research complete. Report size: {len(self.state.get_full_report())} chars", "MessageHandler")
            return True

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
            self.logger.log(f"Deep Research query: {query[:80]}", "MessageHandler")
            return False

        self.logger.log(f"Unknown PATH format: {output}", "MessageHandler")
        return False

    async def handle_message(self, msg_data: Dict[str, Any]) -> bool:
        """
        Dispatch message handling based on type

        Args:
            msg_data (Dict[str, Any]): Message data dictionary

        Returns:
            bool: True if research is complete, False otherwise
        """
        msg_type = msg_data.get("type")

        if msg_type == "logs":
            await self.handle_logs(
                msg_data.get("content", ""),
                msg_data.get("output", ""),
                msg_data.get("metadata")  # ← ADD THIS
            )
        elif msg_type == "report":
            await self.handle_report(msg_data.get("output", ""))
        elif msg_type == "path":
            return await self.handle_path(msg_data.get("output", {}))

        return False

##############################
########## PIPELINE ##########
##############################


class Pipe:
    class Valves(BaseModel):
        """
        Configuration valves for GPT Researcher Pipe Function
        """
        # Connection
        GPT_RESEARCHER_WS_URL: str = Field(
            default="ws://gptresearcher-server:8000/ws",
            description="WebSocket URL of GPT Researcher container",
        )

        # Model Configuration
        DEFAULT_MODEL: str = Field(
            default="llama3.2:latest",
            description="Model for classification and follow-ups",
        )

        # Research Settings
        REPORT_SOURCE: str = Field(
            default="web", description="Source: 'web', 'local', 'hybrid'"
        )
        TONE: str = Field(default="Objective", description="Report tone")
        TOTAL_WORDS: int = Field(default=2500, description="Target word count")

        # Deep Research
        DEEP_RESEARCH_BREADTH: int = Field(default=4, description="Parallel paths")
        DEEP_RESEARCH_DEPTH: int = Field(default=2, description="Research depth")

        # Debug
        VERBOSE: bool = Field(default=True, description="Enable verbose logging")

    def __init__(self):
        """Constructor for GPT Researcher Pipe"""
        self.emitter: Union[Callable[[Dict[str, Any]], Awaitable[None]], None] = None
        self.event_call = None
        self.body: Union[dict, None] = None
        self.user: Union[dict, None] = None
        self.request: Union[Request, None] = None
        self.logger: Union[Logger, None] = None
        self.model_caller: Union[ModelCaller, None] = None
        self.completion_marker = "\n\n✅ **Recherche abgeschlossen!**"
        self.valves = self.Valves()

    ##########################
    ######## CHECKER #########
    ##########################

    def is_auto_message(self) -> bool:
        """
        Check if the last message is an automatic prompt from OpenWebUI (stream=false)

        Returns:
            bool: True if last message is an automatic prompt, False otherwise
        """
        last_message = self.get_messages()[-1]
        return last_message.get("role") == "user" and self.body.get("stream") is False

    #########################
    ######## GETTER #########
    #########################

    def get_messages(self) -> List[Dict[str, str]]:
        """
        Get messages from the request body

        Returns:
            List[Dict[str, str]]: List of message dictionaries
        """
        if not self.body:
            return []
        messages = self.body.get("messages", [])
        if not messages or not messages[-1].get("content", ""):
            return []
        return messages

    def get_message_count(self) -> int:
        """
        Get the count of messages in the request body

        Returns:
            int: Number of messages
        """
        messages = self.get_messages()
        return len(messages)

    def get_message(self, index: int, max_length: int = 0, from_end: bool = False) -> str:
        """
        Get the content of a specific message by index

        Args:
            index (int): Index of the message to retrieve
            max_length (int): If >0, limit message length
            from_end (bool): If True, take max_length from end, otherwise from start

        Returns:
            str: Content of the message or empty string
        """
        messages = self.get_messages()
        if not messages:
            raise IndexError("No messages available")

        try:
            message = messages[index].get("content", "")
        except IndexError:
            raise IndexError(f"Message index {index} out of range (have {len(messages)} messages)")

        if max_length > 0:
            return message[-max_length:] if from_end else message[:max_length]
        return message

    def get_last_message(self, max_length: int = 0, from_end: bool = False) -> str:
        """
        Get the content of the last message

        Args:
            max_length (int): If >0, limit message length
            from_end (bool): If True, take max_length from end, otherwise from start

        Returns:
            str: Content of the last message or empty string
        """
        return self.get_message(-1, max_length, from_end)

    def get_multiple_messages(self, amount: int = 0, from_end: bool = True, max_length: int = 0, length_from_end: bool = False) -> List[str]:
        """
        Get multiple messages from the request body

        Args:
            amount (int): Number of messages to retrieve. If 0, get all messages.
            from_end (bool): If True, get the last N messages, otherwise get first N messages. Default is True.
            max_length (int): If >0, limit each message's length
            length_from_end (bool): If True, take max_length from end of each message, otherwise from start

        Returns:
            List[str]: List of message contents in chronological order

        Examples:
            >>> # Get last 3 messages
            >>> get_multiple_messages(amount=3, from_end=True)
            ['msg3', 'msg4', 'msg5']  # Chronological order

            >>> # Get first 2 messages
            >>> get_multiple_messages(amount=2, from_end=False)
            ['msg1', 'msg2']
        """
        messages = self.get_messages()
        message_count = len(messages)

        if message_count == 0:
            return []

        # Determine how many messages to get
        num_to_get = amount if amount > 0 else message_count
        num_to_get = min(num_to_get, message_count)  # Don't exceed available messages

        # Get the slice of messages we want
        if from_end:
            # Get last N messages (but keep chronological order)
            start_index = message_count - num_to_get
            selected_indices = range(start_index, message_count)
        else:
            # Get first N messages
            selected_indices = range(0, num_to_get)

        # Extract and optionally truncate messages
        result = []
        for i in selected_indices:
            message = self.get_message(i, max_length, length_from_end)
            result.append(message)

        return result

    #########################
    ######## PROCESS ########
    #########################

    async def pipe(self, body: dict, __user__: dict = None, __request__: Request = None, __event_emitter__=None, __event_call__=None) -> str:
        """
        Main entry point of the function pipe.
        Gets called on each request from OpenWebUI.

        Args:
            body (dict): The request body containing messages and other data.
            __user__ (dict, optional): User information. Defaults to None.
            __request__ (Request, optional): The request object. Defaults to None.
            __event_emitter__ (callable, optional): Function to emit events back to OpenWebUI. Defaults to None.
            __event_call__ (callable, optional): Function to call OpenWebUI tools/functions. Defaults to None.

        Returns:
            str: Response message to return to OpenWebUI
        """
        # init logger
        self.logger = Logger(verbose=self.valves.VERBOSE)
        self.logger.log("New request received", "PIPE", True)
        self.logger.log(f"Request body: {body}", "PIPE", False)

        # make sure emitter is available for preventing crash if not provided
        async def dummy_emitter(*args, **kwargs):
            pass

        # init class variables
        self.emitter = __event_emitter__ if __event_emitter__ else dummy_emitter
        self.user = __user__
        self.event_call = __event_call__
        self.body = body
        self.request = __request__
        self.model_caller = ModelCaller(logger=self.logger, model=self.valves.DEFAULT_MODEL, user=self.user, request=self.request)

        # make sure there is a message to process
        if not self.get_last_message():
            return "❌ Error: No messages provided or message content is empty"
        self.logger.log(f"Current message: {self.get_last_message(60)}", "PIPE", False)

        # Detect conversation stage
        stage = self._detect_conversation_stage()

        # Handle follow ups
        if stage == "follow_up":
            # on follow up we pass the call to the default model directly
            return await self.model_caller.do_prompt(messages=self.get_messages())

        if stage == "ongoing":
            # ongoing conversation - we simply use same logic as initial
            stage = "initial"

        # Hande initial messages
        research_type = None
        if stage == "initial":
            # we use default model to analyse the initial input. We check if there are enough details given
            analysis = await self.analyze_user_input()
            self.logger.log(f"Analysis result: {analysis}", "PIPE", False)
            # if we need more infos, we ask the user
            if not analysis.get("is_ready", False):
                return analysis["question"]  # proceed to type selection
            # if we have enough infos, we move to research stage
            stage = "ready_for_research"
            query = analysis["summary"]
            research_type = analysis["type"]

        if stage == "ready_for_research":
            # we have enough infos, we start the research directly
            research_name = "Tiefenrecherche" if research_type == "deep" else "Recherche"
            confirmation = f"🔍 Okay, ich starte eine **{research_name}** zu: '{query}'...\n\n"

            # Research
            report = await self._conduct_research(query, research_type)
            self.logger.log("Research completed", "PIPE", False)

            # Print results
            return f"{confirmation}{report}{self.completion_marker}"

    def _detect_conversation_stage(self) -> str:
        """
        Detect the current stage in the conversation

        Returns:
            str: One of 'initial', 'ongoing', 'follow_up'

        """
        # check if the last message is an automatic prompt
        if self.is_auto_message():
            self.logger.log("auto_suggestion detected", "STAGE DETECTION")
            return "follow_up"

        # if its the first message and not auto message, it's the initial message
        if self.get_message_count() == 1:
            self.logger.log("initial detected", "STAGE DETECTION")
            return "initial"

        # if there are more messages, we are in ongoing conversation
        if self.get_message_count() > 1:
            # iterate all messages and search for completion marker
            for msg in self.get_multiple_messages():
                if self.completion_marker in msg:
                    self.logger.log("follow_up detected", "STAGE DETECTION")
                    return "follow_up"

            self.logger.log("ongoing conversation detected", "STAGE DETECTION")
            return "ongoing"

    async def analyze_user_input(self) -> dict:
        """
        Refine user input to check if enough details are provided for research

        Returns:
            dict: Refinement result with 'is_ready', 'type', 'question', and 'summary' fields

        Raises:
            ValueError: If refinement model does not return valid JSON
        """
        research_analyzer_prompt = """
        Du bist ein präziser Analyse-Assistent für Rechercheaufträge. Deine Aufgabe ist es, einen vorliegenden Chatverlauf zwischen einem Nutzer und einer KI zu analysieren. Prüfe, ob die Summe aller Nutzerantworten ausreicht, um den Rechercheauftrag vollständig und eindeutig auszuführen.

        **Analyse-Logik:**
        Betrachte den gesamten bisherigen Gesprächsverlauf. Sobald alle benötigten Informationen vorhanden sind, setze "is_ready" auf true.

        **Kriterien für ein "is_ready: true":**
        1. **Subjekt/Objekt:** Ist klar definiert, wer oder was recherchiert werden soll?
        2. **Fokus/Kontext:** Wurde eine spezifische Fragestellung oder ein Zielbereich festgelegt?
        3. **Umfang & Typ:** Ist klar, ob eine Standard-Recherche (research_report) oder eine komplexe Tiefenanalyse (deep) gewünscht ist?

        **Definition der Typen (Feld "type"):**
        - **research_report:** Standardwert für normale Informationsabfragen, Biografien oder Fakten-Checks.
        - **deep:** Zu wählen bei hoher Komplexität, wissenschaftlichen Fragestellungen, umfangreichen Marktanalysen oder wenn der Nutzer explizit eine "sehr tiefe" oder "umfassende" Analyse fordert.
        - **Wichtig:** Wenn aus dem Verlauf nicht hervorgeht, welche Tiefe benötigt wird, setze "is_ready" auf false und frage in "question" explizit nach, ob ein kompakter Report oder eine komplexe Tiefenanalyse gewünscht ist.

        **Anforderungen an die Felder:**
        - **is_ready:** boolean.
        - **type:** "research_report", "deep" oder null (wenn is_ready false).
        - **question:** Falls Infos fehlen oder der Typ unklar ist: Eine höfliche Rückfrage in der Nutzersprache. Falls is_ready true: null.
        - **summary:** Falls is_ready true: Eine präzise, konsolidierte Zusammenfassung des Auftrags in der Nutzersprache als Aufforderung formuliert. Falls is_ready false: null.

        **Ausgabeformat:**
        Antworte ausschließlich im JSON-Format ohne Text davor oder danach.

        {
        "is_ready": boolean,
        "type": "research_report" | "deep" | null,
        "question": "String oder null",
        "summary": "String oder null"
        }
        """.strip()
        # call the model
        json_string = await self.model_caller.do_prompt(
            prompt=research_analyzer_prompt,
            role="system",
            messages=self.get_messages(),
            response_format={"type": "json_object"})

        try:
            # validate json
            result = json.loads(json_string)
            if not "is_ready" in result:
                raise ValueError("Refinement model did not return 'is_ready' field")
            if not "question" in result:
                raise ValueError("Refinement model did not return 'question' field")
            if not "type" in result:
                raise ValueError("Refinement model did not return 'type' field")
            if not "summary" in result:
                raise ValueError("Refinement model did not return 'summary' field")

            # strip question
            result["question"] = result["question"].strip() if result["question"] else None

            # check consistency
            if not result["is_ready"] and not result["question"]:
                raise ValueError("Refinement model returned 'is_ready' false but no question")
            if result["is_ready"] and not result["type"]:
                raise ValueError("Refinement model returned 'is_ready' true but no type")
            if result["is_ready"] and not result["summary"]:
                raise ValueError("Refinement model returned 'is_ready' true but no summary")
            return result
        except json.JSONDecodeError:
            raise ValueError("Refinement model did not return valid JSON")

    async def _conduct_research(self, query: str, report_type: str) -> str:
        """
        Execute research and return report

        Args:
            query (str): Research query
            report_type (str): Type of report ('research_report' or 'deep')

        Returns:
            str: Generated research report
        """
        self.logger.log(f"Starting research: '{query}...', Type: {report_type}", "CONDUCT_RESEARCH", True)
        state = ResearchState()
        handler = MessageHandler(state, self.logger, self.emitter, self.valves.VERBOSE)

        try:
            await self.emitter(
                {
                    "type": "status",
                    "data": {"description": "Bereite Research Engine vor...", "done": False},
                }
            )

            request_config = self._build_request_config(query, report_type)
            timeout = aiohttp.ClientTimeout(
                total=None, connect=60, sock_connect=60, sock_read=None
            )
            self.logger.log(f"Connecting to WebSocket at {self.valves.GPT_RESEARCHER_WS_URL}", "CONDUCT_RESEARCH", False)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.ws_connect(
                    self.valves.GPT_RESEARCHER_WS_URL, heartbeat=30
                ) as ws:

                    start_msg = f"start {json.dumps(request_config)}"
                    await ws.send_str(start_msg)
                    self.logger.log(f"Sent start command: {start_msg}", "CONDUCT_RESEARCH", False)
                    await self._handle_websocket_stream(ws, handler)

            report = state.get_full_report()
            self.logger.log(
                f"[RESEARCH DONE] Report size: {len(report)} chars", "CONDUCT_RESEARCH", False
            )

            if report:
                return report
            else:
                self.logger.log("[RESEARCH] ⚠️ No report generated", "CONDUCT_RESEARCH", False)
                return "⚠️ Research abgeschlossen, aber kein Report generiert."

        except Exception as e:
            self.logger.log(f"[RESEARCH] ❌ Error during research: {str(e)}", "CONDUCT_RESEARCH", False)
            traceback.print_exc()
            report = state.get_full_report()
            if report:
                self.logger.log(f"[RESEARCH] Partial report size: {len(report)} chars", "CONDUCT_RESEARCH", False)
                return f"{report}\n\n---\n⚠️ Verbindung unterbrochen, Partial-Report."
            return f"❌ Research error: {str(e)}"

    def _build_request_config(self, query: str, report_type: str) -> Dict[str, Any]:
        """
        Build research request config

        Args:
            query (str): Research query
            report_type (str): Type of report ('research_report' or 'deep')

        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        config = {
            "task": query,
            "report_type": report_type,
            "report_source": self.valves.REPORT_SOURCE,
            "source_urls": [],
            "tone": self.valves.TONE,
            "agent": "Auto Agent",
            "total_words": self.valves.TOTAL_WORDS,
        }

        if report_type == "deep":
            config["deep_research_breadth"] = self.valves.DEEP_RESEARCH_BREADTH
            config["deep_research_depth"] = self.valves.DEEP_RESEARCH_DEPTH

        self.logger.log(f"Request config: {config}", "BUILD_CONFIG", False)
        return config

    async def _handle_websocket_stream(self, ws: aiohttp.ClientWebSocketResponse, handler: MessageHandler) -> None:
        """
        Process WebSocket stream until completion

        Args:
            ws (aiohttp.ClientWebSocketResponse): WebSocket connection
            handler (MessageHandler): Message handler instance

        Returns:
            None
        """
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = msg.data

                if data == "ping":
                    await ws.send_str("pong")
                    continue

                if data.startswith('{"type":'):
                    try:
                        msg_data = json.loads(data)
                        should_end = await handler.handle_message(msg_data)
                        if should_end:
                            break
                    except json.JSONDecodeError as e:
                        self.logger.log(f"[WS] JSON Error: {e}", "HANDLE_WS_STREAM", False)
                        continue

            elif msg.type == aiohttp.WSMsgType.ERROR:
                self.logger.log(f"[WS] ❌ Error: {ws.exception()}", "HANDLE_WS_STREAM", False)
                break
            elif msg.type == aiohttp.WSMsgType.CLOSE:
                self.logger.log("[WS] Connection closed", "HANDLE_WS_STREAM", False)
                break
