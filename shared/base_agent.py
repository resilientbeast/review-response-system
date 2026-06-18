"""Base SimpleAdapter subclass used by all review pipeline agents."""

from __future__ import annotations

import logging
import re
from openai import AsyncOpenAI
from band.core.simple_adapter import SimpleAdapter
from band.core.types import PlatformMessage

from shared.config import FEATHERLESS_BASE

logger = logging.getLogger(__name__)

# Regex to strip Qwen3-style <think>...</think> blocks (safety net)
_THINK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL)

# Regex to strip Band @mention prefixes: @[[uuid]] or @[[uuid/name]]
_MENTION_PREFIX_RE = re.compile(r"@\[\[[^\]]*\]\]\s*")


class ReviewAgentAdapter(SimpleAdapter):
    """
    Base adapter for all six review pipeline agents.

    Extend this class and override `process_message()`.
    Band SDK calls `on_message()` when a message arrives.

    Key contract:
    - NEVER use return values to communicate — only `tools.send_message()`
    - ALWAYS call `tools.send_event()` for status updates (visible in Band room)
    - ALWAYS validate schemas before routing to next agent
    """

    def __init__(
        self,
        agent_name: str,
        llm_base_url: str,
        llm_api_key: str,
        model: str,
    ):
        super().__init__()                  # SimpleAdapter requires no args
        self.agent_name = agent_name
        self.model = model
        self._is_featherless = llm_base_url.rstrip("/") == FEATHERLESS_BASE.rstrip("/")
        self.log = logging.getLogger(agent_name)

        self.llm = AsyncOpenAI(
            base_url=llm_base_url,
            api_key=llm_api_key,
        )

    async def on_message(
        self,
        msg: PlatformMessage,
        tools,                              # AgentToolsProtocol
        history,                            # HistoryProvider (ignored — we use msg.content)
        participants_msg: str | None,
        contacts_msg: str | None,
        *,
        is_session_bootstrap: bool,
        room_id: str,
    ) -> None:
        """
        Called by Band SDK when a message arrives addressed to this agent.
        Delegates to process_message() which subclasses implement.
        """
        if is_session_bootstrap:
            self.log.info(f"{self.agent_name} session bootstrapping in room {room_id}")

        # Strip Band mention prefixes (e.g., @[[uuid]]) from message content
        content = _MENTION_PREFIX_RE.sub("", msg.content).strip()
        self.log.info(f"Message received ({len(content)} chars) from {msg.sender_name}")
        try:
            await self.process_message(content, tools)
        except Exception as e:
            self.log.error(f"Error in process_message: {e}", exc_info=True)
            await tools.send_event(
                content=f"[{self.agent_name}] Error: {str(e)[:300]}",
                message_type="error",
            )

    async def process_message(self, content: str, tools) -> None:
        """Override in each agent subclass."""
        raise NotImplementedError(f"{self.agent_name}.process_message() must be implemented")

    @staticmethod
    def _strip_thinking(text: str) -> str:
        """Remove Qwen3-style <think>...</think> blocks from LLM output."""
        return _THINK_RE.sub("", text).strip()

    async def call_llm(
        self,
        system_prompt: str,
        user_content: str,
        json_mode: bool = True,
    ) -> str:
        """Call the configured LLM. Returns clean response text.

        For Featherless (Qwen3) models: disables thinking tokens via
        extra_body to prevent <think> blocks from breaking JSON parsing.
        Also applies a regex safety net to strip any residual tokens.
        """
        kwargs: dict = dict(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_content},
            ],
            max_tokens=2048,
            temperature=0.3,
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        # Qwen3 models emit <think> blocks by default — disable them
        if self._is_featherless:
            kwargs["extra_body"] = {
                "chat_template_kwargs": {"enable_thinking": False}
            }

        resp = await self.llm.chat.completions.create(**kwargs)
        text = resp.choices[0].message.content

        # Safety net: strip any residual thinking tokens
        text = self._strip_thinking(text)
        return text

    async def post_status(self, tools, message: str) -> None:
        """Post a human-readable thought event to the Band room."""
        await tools.send_event(content=message, message_type="thought")
