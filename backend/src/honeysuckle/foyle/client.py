"""Claude Agent SDK wrapper for Foyle."""

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from honeysuckle.foyle.prompts import FOYLE_SYSTEM_PROMPT


@dataclass
class FoyleEvent:
    """Base class for Foyle events."""

    pass


@dataclass
class ToolStart(FoyleEvent):
    """Tool execution started."""

    name: str
    input: dict[str, Any]


@dataclass
class ToolEnd(FoyleEvent):
    """Tool execution completed."""

    name: str
    output: str


@dataclass
class ApprovalNeeded(FoyleEvent):
    """Approval required for tool execution."""

    tool: str
    input: dict[str, Any]
    description: str


@dataclass
class TextDelta(FoyleEvent):
    """Text output from Foyle."""

    text: str


@dataclass
class Result(FoyleEvent):
    """Final result from Foyle."""

    text: str


ApprovalCallback = Callable[[str, dict[str, Any], str], bool]


class FoyleClient:
    """
    Claude Agent SDK client for deep reasoning and tool execution.

    Foyle handles complex requests that require:
    - Multi-turn reasoning
    - Tool execution (gday CLI for email/calendar)
    - Human-in-the-loop approval flows
    """

    def __init__(self, approval_callback: ApprovalCallback | None = None):
        """
        Initialize Foyle client.

        Args:
            approval_callback: Async function to request user approval.
                Signature: (tool_name, tool_input, description) -> bool
        """
        self.approval_callback = approval_callback
        self._cancel_event: asyncio.Event | None = None

    async def run(self, query_text: str) -> AsyncIterator[FoyleEvent]:
        """
        Run a query through Foyle.

        Yields events as Foyle reasons and executes tools.
        Final event is always a Result with the response text.

        Args:
            query_text: The user's request to process
        """
        self._cancel_event = asyncio.Event()

        options = ClaudeAgentOptions(
            system_prompt=FOYLE_SYSTEM_PROMPT,
            allowed_tools=["Bash"],  # gday CLI access
            max_turns=10,
            permission_mode="bypassPermissions",  # We handle approval ourselves
        )

        final_text = ""

        try:
            async for message in query(prompt=query_text, options=options):
                # Check for cancellation
                if self._cancel_event.is_set():
                    break

                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            yield TextDelta(text=block.text)
                            final_text = block.text
                        elif isinstance(block, ToolUseBlock):
                            yield ToolStart(name=block.name, input=block.input)

                elif isinstance(message, ResultMessage):
                    # Final result
                    if message.result:
                        final_text = message.result
                    yield Result(text=final_text)
                    return

        except Exception as e:
            yield Result(text=f"Error processing request: {e}")

    async def cancel(self):
        """Cancel the current Foyle task."""
        if self._cancel_event:
            self._cancel_event.set()
