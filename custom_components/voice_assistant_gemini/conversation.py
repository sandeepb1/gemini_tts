"""Conversation agent for Google Gemini."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    API_TIMEOUT,
    RETRY_ATTEMPTS,
    RETRY_BACKOFF_FACTOR,
)
from .gemini_client import GeminiClient, GeminiAPIError

_LOGGER = logging.getLogger(__name__)


class GeminiAgent:
    """Google Gemini conversation agent."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_key: str,
        model: str = "gemini-2.0-flash",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        coordinator=None,
    ) -> None:
        """Initialize the Gemini agent."""
        self.hass = hass
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.coordinator = coordinator
        self._client = None
        self._retry_count = 0

    async def _get_client(self):
        """Get Gemini client."""
        if self._client is None:
            try:
                self._client = GeminiClient(self.api_key, self.hass)
            except Exception as err:
                _LOGGER.error("Error initializing Gemini client: %s", err)
                raise RuntimeError(f"Failed to initialize Gemini client: {err}") from err
        
        return self._client

    async def generate(
        self,
        prompt: str,
        session_id: str | None = None,
        system_prompt: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Generate response using Gemini."""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        try:
            # Get session history
            session_data = await self._get_session_data(session_id)
            
            # Build conversation context
            conversation_history = session_data.get("history", [])
            
            # Prepare the full conversation
            messages = []
            
            # Add system prompt if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Add conversation history
            messages.extend(conversation_history)
            
            # Add current user message
            messages.append({"role": "user", "content": prompt})
            
            # Generate response
            response_text = await self._generate_response(messages)
            
            # Update session history
            conversation_history.append({"role": "user", "content": prompt})
            conversation_history.append({"role": "assistant", "content": response_text})
            
            # Keep only last 20 messages to prevent token limit issues
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]
            
            # Save session data
            session_data.update({
                "history": conversation_history,
                "last_interaction": datetime.now().isoformat(),
                "created_at": session_data.get("created_at") or datetime.now().isoformat(),
            })
            
            await self._save_session_data(session_id, session_data)
            
            metadata = {
                "session_id": session_id,
                "model": self.model,
                "temperature": self.temperature,
                "message_count": len(conversation_history),
                "timestamp": datetime.now().isoformat(),
            }
            
            _LOGGER.debug(
                "Generated response for session %s: %d characters",
                session_id, len(response_text)
            )
            
            self._retry_count = 0  # Reset retry count on success
            return response_text, metadata
        
        except Exception as err:
            self._retry_count += 1
            if self._retry_count < RETRY_ATTEMPTS:
                backoff_time = RETRY_BACKOFF_FACTOR ** self._retry_count
                _LOGGER.warning(
                    "Gemini generation failed (attempt %d): %s. Retrying in %d seconds",
                    self._retry_count, err, backoff_time
                )
                await asyncio.sleep(backoff_time)
                return await self.generate(prompt, session_id, system_prompt)
            
            _LOGGER.error("Gemini generation failed after %d attempts: %s", RETRY_ATTEMPTS, err)
            raise RuntimeError(f"Conversation generation failed: {err}") from err

    async def _generate_response(self, messages: list[dict[str, str]]) -> str:
        """Generate response using Gemini API."""
        try:
            client = await self._get_client()
            
            # Use the new conversation method
            response_text = await client.conversation(messages)
            
            if not response_text:
                raise RuntimeError("Empty response from Gemini")
            
            return response_text.strip()
        
        except GeminiAPIError as err:
            _LOGGER.error("Gemini API generation error: %s", err)
            raise RuntimeError(f"Gemini API error: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error in response generation: %s", err)
            raise

    def _convert_messages_to_prompt(self, messages: list[dict[str, str]]) -> str:
        """Convert message history to Gemini prompt format."""
        prompt_parts = []
        
        for message in messages:
            role = message["role"]
            content = message["content"]
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"Human: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        # Add final prompt for assistant response
        prompt_parts.append("Assistant:")
        
        return "\n\n".join(prompt_parts)

    async def _get_session_data(self, session_id: str) -> dict[str, Any]:
        """Get session data from coordinator."""
        if self.coordinator:
            return await self.coordinator.async_get_session_data(session_id)
        return {"history": [], "created_at": None, "last_interaction": None}

    async def _save_session_data(self, session_id: str, session_data: dict[str, Any]) -> None:
        """Save session data through coordinator."""
        if self.coordinator:
            await self.coordinator.async_save_session_data(session_id, session_data)

    async def clear_session(self, session_id: str) -> None:
        """Clear a conversation session."""
        if self.coordinator:
            await self.coordinator.async_clear_session(session_id)
        _LOGGER.info("Cleared conversation session: %s", session_id)

    async def get_session_history(self, session_id: str) -> list[dict[str, str]]:
        """Get conversation history for a session."""
        session_data = await self._get_session_data(session_id)
        return session_data.get("history", [])

    async def get_active_sessions(self) -> list[str]:
        """Get list of active session IDs."""
        if not self.coordinator:
            return []
        
        storage_data = await self.coordinator.store.async_load() or {}
        sessions = storage_data.get("sessions", {})
        return list(sessions.keys())

    async def prune_sessions(self, max_age_days: int = 7) -> int:
        """Prune old conversation sessions."""
        if not self.coordinator:
            return 0
        
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        storage_data = await self.coordinator.store.async_load() or {}
        sessions = storage_data.get("sessions", {})
        
        sessions_to_remove = []
        for session_id, session_data in sessions.items():
            try:
                last_interaction = datetime.fromisoformat(
                    session_data.get("last_interaction", "")
                )
                if last_interaction < cutoff_date:
                    sessions_to_remove.append(session_id)
            except (ValueError, TypeError):
                # Invalid date format, mark for removal
                sessions_to_remove.append(session_id)
        
        # Remove old sessions
        for session_id in sessions_to_remove:
            sessions.pop(session_id, None)
        
        if sessions_to_remove:
            storage_data["sessions"] = sessions
            await self.coordinator.store.async_save(storage_data)
            _LOGGER.info("Pruned %d old conversation sessions", len(sessions_to_remove))
        
        return len(sessions_to_remove)

    async def get_session_stats(self) -> dict[str, Any]:
        """Get statistics about conversation sessions."""
        if not self.coordinator:
            return {}
        
        storage_data = await self.coordinator.store.async_load() or {}
        sessions = storage_data.get("sessions", {})
        
        total_sessions = len(sessions)
        total_messages = sum(
            len(session.get("history", []))
            for session in sessions.values()
        )
        
        # Calculate active sessions (last 24 hours)
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(hours=24)
        active_sessions = 0
        
        for session_data in sessions.values():
            try:
                last_interaction = datetime.fromisoformat(
                    session_data.get("last_interaction", "")
                )
                if last_interaction > cutoff_time:
                    active_sessions += 1
            except (ValueError, TypeError):
                continue
        
        return {
            "total_sessions": total_sessions,
            "active_sessions_24h": active_sessions,
            "total_messages": total_messages,
            "average_messages_per_session": total_messages / max(total_sessions, 1),
        }

    async def test_connection(self) -> bool:
        """Test the Gemini connection."""
        try:
            client = await self._get_client()
            return await client.test_connection()
        except Exception as err:
            _LOGGER.error("Gemini connection test failed: %s", err)
            return False

    async def generate_summary(self, session_id: str) -> str:
        """Generate a summary of the conversation session."""
        try:
            history = await self.get_session_history(session_id)
            if not history:
                return "No conversation history found."
            
            # Create summary prompt
            conversation_text = "\n".join([
                f"{msg['role'].title()}: {msg['content']}"
                for msg in history
            ])
            
            summary_prompt = f"""Please provide a brief summary of this conversation:

{conversation_text}

Summary:"""
            
            # Generate summary using the new client
            client = await self._get_client()
            summary = await client.generate_text(summary_prompt)
            return summary.strip() if summary else "Unable to generate summary."
        
        except Exception as err:
            _LOGGER.error("Error generating summary: %s", err)
            return f"Error generating summary: {err}" 