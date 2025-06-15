"""Test the Voice Assistant Gemini conversation agent."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from custom_components.voice_assistant_gemini.conversation import GeminiAgent


@pytest.mark.asyncio
async def test_gemini_agent_generate_success(mock_hass, mock_gemini, mock_store):
    """Test successful conversation generation."""
    agent = GeminiAgent(
        mock_hass, "test_api_key", "gemini-pro", 0.7, 2048, 
        coordinator=Mock(async_get_session_data=AsyncMock(return_value={"history": []}),
                        async_save_session_data=AsyncMock())
    )
    
    response_text, metadata = await agent.generate("Hello", "test_session")
    
    assert response_text == "This is a test response from Gemini."
    assert metadata["session_id"] == "test_session"
    assert metadata["model"] == "gemini-pro"
    assert metadata["temperature"] == 0.7


@pytest.mark.asyncio
async def test_gemini_agent_with_system_prompt(mock_hass, mock_gemini, mock_store):
    """Test conversation with system prompt."""
    agent = GeminiAgent(
        mock_hass, "test_api_key", "gemini-pro", 0.7, 2048,
        coordinator=Mock(async_get_session_data=AsyncMock(return_value={"history": []}),
                        async_save_session_data=AsyncMock())
    )
    
    response_text, metadata = await agent.generate(
        "Hello", "test_session", "You are a helpful assistant."
    )
    
    assert response_text == "This is a test response from Gemini."


@pytest.mark.asyncio
async def test_gemini_agent_with_history(mock_hass, mock_gemini, mock_store):
    """Test conversation with existing history."""
    history = [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"}
    ]
    
    agent = GeminiAgent(
        mock_hass, "test_api_key", "gemini-pro", 0.7, 2048,
        coordinator=Mock(async_get_session_data=AsyncMock(return_value={"history": history}),
                        async_save_session_data=AsyncMock())
    )
    
    response_text, metadata = await agent.generate("Follow up question", "test_session")
    
    assert response_text == "This is a test response from Gemini."
    assert metadata["message_count"] == 4  # 2 previous + 2 new


@pytest.mark.asyncio
async def test_gemini_agent_history_truncation(mock_hass, mock_gemini, mock_store):
    """Test conversation history truncation."""
    # Create history with more than 20 messages
    history = []
    for i in range(22):
        history.extend([
            {"role": "user", "content": f"Question {i}"},
            {"role": "assistant", "content": f"Answer {i}"}
        ])
    
    mock_coordinator = Mock()
    mock_coordinator.async_get_session_data = AsyncMock(return_value={"history": history})
    mock_coordinator.async_save_session_data = AsyncMock()
    
    agent = GeminiAgent(mock_hass, "test_api_key", "gemini-pro", 0.7, 2048, mock_coordinator)
    
    response_text, metadata = await agent.generate("New question", "test_session")
    
    # Should have truncated to last 20 messages + 2 new = 22 total
    # But we limit to 20, so should be exactly 20
    saved_session_data = mock_coordinator.async_save_session_data.call_args[0][1]
    assert len(saved_session_data["history"]) == 20


@pytest.mark.asyncio
async def test_gemini_agent_error_handling(mock_hass, mock_store):
    """Test error handling in conversation generation."""
    with patch("google.generativeai.GenerativeModel") as mock_model:
        mock_model.return_value.generate_content.side_effect = Exception("API Error")
        
        agent = GeminiAgent(
            mock_hass, "test_api_key", "gemini-pro", 0.7, 2048,
            coordinator=Mock(async_get_session_data=AsyncMock(return_value={"history": []}),
                            async_save_session_data=AsyncMock())
        )
        
        with pytest.raises(RuntimeError):
            await agent.generate("Hello", "test_session")


@pytest.mark.asyncio
async def test_gemini_agent_retry_mechanism(mock_hass, mock_store):
    """Test retry mechanism on failures."""
    with patch("google.generativeai.GenerativeModel") as mock_model:
        # First call fails, second succeeds
        mock_response = Mock()
        mock_response.text = "Retry success"
        
        mock_model.return_value.generate_content.side_effect = [
            Exception("Temporary error"),
            mock_response
        ]
        
        agent = GeminiAgent(
            mock_hass, "test_api_key", "gemini-pro", 0.7, 2048,
            coordinator=Mock(async_get_session_data=AsyncMock(return_value={"history": []}),
                            async_save_session_data=AsyncMock())
        )
        
        with patch("asyncio.sleep"):  # Speed up test
            response_text, metadata = await agent.generate("Hello", "test_session")
        
        assert response_text == "Retry success"
        assert mock_model.return_value.generate_content.call_count == 2


@pytest.mark.asyncio
async def test_gemini_agent_clear_session(mock_hass, mock_store):
    """Test clearing a conversation session."""
    mock_coordinator = Mock()
    mock_coordinator.async_clear_session = AsyncMock()
    
    agent = GeminiAgent(mock_hass, "test_api_key", coordinator=mock_coordinator)
    
    await agent.clear_session("test_session")
    
    mock_coordinator.async_clear_session.assert_called_once_with("test_session")


@pytest.mark.asyncio
async def test_gemini_agent_get_session_history(mock_hass, mock_store):
    """Test getting session history."""
    history = [
        {"role": "user", "content": "Question"},
        {"role": "assistant", "content": "Answer"}
    ]
    
    mock_coordinator = Mock()
    mock_coordinator.async_get_session_data = AsyncMock(return_value={"history": history})
    
    agent = GeminiAgent(mock_hass, "test_api_key", coordinator=mock_coordinator)
    
    result = await agent.get_session_history("test_session")
    
    assert result == history


@pytest.mark.asyncio
async def test_gemini_agent_get_active_sessions(mock_hass, mock_store):
    """Test getting active sessions."""
    mock_coordinator = Mock()
    mock_coordinator.store = Mock()
    mock_coordinator.store.async_load = AsyncMock(return_value={
        "sessions": {
            "session1": {"history": []},
            "session2": {"history": []}
        }
    })
    
    agent = GeminiAgent(mock_hass, "test_api_key", coordinator=mock_coordinator)
    
    sessions = await agent.get_active_sessions()
    
    assert set(sessions) == {"session1", "session2"}


@pytest.mark.asyncio
async def test_gemini_agent_prune_sessions(mock_hass, mock_store):
    """Test pruning old sessions."""
    from datetime import timedelta
    old_date = (datetime.now() - timedelta(days=10)).isoformat()
    recent_date = datetime.now().isoformat()
    
    sessions_data = {
        "sessions": {
            "old_session": {"last_interaction": old_date},
            "recent_session": {"last_interaction": recent_date},
            "invalid_session": {"last_interaction": "invalid_date"}
        }
    }
    
    mock_coordinator = Mock()
    mock_coordinator.store = Mock()
    mock_coordinator.store.async_load = AsyncMock(return_value=sessions_data)
    mock_coordinator.store.async_save = AsyncMock()
    
    agent = GeminiAgent(mock_hass, "test_api_key", coordinator=mock_coordinator)
    
    pruned_count = await agent.prune_sessions(max_age_days=7)
    
    assert pruned_count == 2  # old_session and invalid_session
    mock_coordinator.store.async_save.assert_called_once()


@pytest.mark.asyncio
async def test_gemini_agent_get_session_stats(mock_hass, mock_store):
    """Test getting session statistics."""
    from datetime import timedelta
    recent_date = datetime.now().isoformat()
    old_date = (datetime.now() - timedelta(days=2)).isoformat()
    
    sessions_data = {
        "sessions": {
            "session1": {
                "history": [{"role": "user", "content": "Q1"}, {"role": "assistant", "content": "A1"}],
                "last_interaction": recent_date
            },
            "session2": {
                "history": [{"role": "user", "content": "Q2"}],
                "last_interaction": old_date
            }
        }
    }
    
    mock_coordinator = Mock()
    mock_coordinator.store = Mock()
    mock_coordinator.store.async_load = AsyncMock(return_value=sessions_data)
    
    agent = GeminiAgent(mock_hass, "test_api_key", coordinator=mock_coordinator)
    
    stats = await agent.get_session_stats()
    
    assert stats["total_sessions"] == 2
    assert stats["total_messages"] == 3
    assert stats["active_sessions_24h"] == 1
    assert stats["average_messages_per_session"] == 1.5


@pytest.mark.asyncio
async def test_gemini_agent_test_connection_success(mock_hass, mock_gemini):
    """Test successful connection test."""
    agent = GeminiAgent(mock_hass, "test_api_key")
    
    result = await agent.test_connection()
    
    assert result is True


@pytest.mark.asyncio
async def test_gemini_agent_test_connection_failure(mock_hass):
    """Test failed connection test."""
    with patch("google.generativeai.GenerativeModel") as mock_model:
        mock_model.return_value.generate_content.side_effect = Exception("Connection failed")
        
        agent = GeminiAgent(mock_hass, "test_api_key")
        
        result = await agent.test_connection()
        
        assert result is False


@pytest.mark.asyncio
async def test_gemini_agent_generate_summary(mock_hass, mock_gemini):
    """Test generating conversation summary."""
    history = [
        {"role": "user", "content": "What is Python?"},
        {"role": "assistant", "content": "Python is a programming language."},
        {"role": "user", "content": "How do I install it?"},
        {"role": "assistant", "content": "You can download it from python.org."}
    ]
    
    mock_coordinator = Mock()
    mock_coordinator.async_get_session_data = AsyncMock(return_value={"history": history})
    
    agent = GeminiAgent(mock_hass, "test_api_key", coordinator=mock_coordinator)
    
    summary = await agent.generate_summary("test_session")
    
    assert summary == "This is a test response from Gemini."


@pytest.mark.asyncio
async def test_gemini_agent_generate_summary_empty_history(mock_hass):
    """Test generating summary with empty history."""
    mock_coordinator = Mock()
    mock_coordinator.async_get_session_data = AsyncMock(return_value={"history": []})
    
    agent = GeminiAgent(mock_hass, "test_api_key", coordinator=mock_coordinator)
    
    summary = await agent.generate_summary("test_session")
    
    assert summary == "No conversation history found." 