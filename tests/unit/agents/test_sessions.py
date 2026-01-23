"""
Unit tests for SessionManager class.

Tests session creation, management, and the specific fixes made in Phase 1:
- SQL $2 syntax errors in session queries
- Session state management
- Message handling within sessions
"""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta

from app.agents.sessions import SessionManager, SessionConfig, SessionStatus


class TestSessionManager:
    """Test suite for SessionManager class."""

    @pytest.fixture
    def session_manager(self):
        """Create a fresh SessionManager instance for each test."""
        return SessionManager()

    @pytest.fixture
    def sample_session_data(self):
        """Create sample session data for testing."""
        return {
            "id": str(uuid.uuid4()),
            "agent_id": str(uuid.uuid4()),
            "user_id": "test_user",
            "state": "active",
            "context": {"topic": "testing"},
            "metadata": {"source": "test"},
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "ended_at": None
        }

    @pytest.mark.asyncio
    async def test_create_session_success(self, session_manager):
        """Test successful session creation."""
        # Setup
        agent_id = str(uuid.uuid4())
        user_id = "test_user"
        config = SessionConfig(
            max_messages=100,
            timeout_minutes=30,
            context={"topic": "testing"}
        )

        # Mock database insert
        with patch('app.agents.sessions.db') as mock_db:
            mock_db.fetch_one = AsyncMock(return_value={"id": uuid.uuid4()})

            # Execute
            session = await session_manager.create_session(
                agent_id=agent_id,
                user_id=user_id,
                config=config
            )

            # Verify
            assert session is not None
            assert session.agent_id == agent_id
            assert session.user_id == user_id
            assert session.state == SessionStatus.ACTIVE

            # Verify database query (checking for $2 syntax fix)
            mock_db.fetch_one.assert_called_once()
            call_args = mock_db.fetch_one.call_args[0][0]
            # Should not have syntax errors with $ parameter numbering
            assert "$1" in call_args
            assert "$2" in call_args
            assert "$3" in call_args
            # Check all required parameters are in the query
            assert "INSERT INTO sessions" in call_args

    @pytest.mark.asyncio
    async def test_create_session_minimal_config(self, session_manager):
        """Test session creation with minimal configuration."""
        # Setup
        agent_id = str(uuid.uuid4())
        user_id = "test_user"

        # Mock database
        with patch('app.agents.sessions.db') as mock_db:
            mock_db.fetch_one = AsyncMock(return_value={"id": uuid.uuid4()})

            # Execute without config
            session = await session_manager.create_session(
                agent_id=agent_id,
                user_id=user_id
            )

            # Verify
            assert session is not None
            assert session.config.max_messages == 50  # default
            assert session.config.timeout_minutes == 60  # default

    @pytest.mark.asyncio
    async def test_get_session_success(self, session_manager, sample_session_data):
        """Test successful session retrieval."""
        # Setup
        session_id = sample_session_data["id"]

        # Mock database query
        with patch('app.agents.sessions.db') as mock_db:
            mock_db.fetch_one = AsyncMock(return_value=sample_session_data)

            # Execute
            session = await session_manager.get_session(session_id)

            # Verify
            assert session is not None
            assert session.id == session_id
            assert session.agent_id == sample_session_data["agent_id"]
            assert session.state.value == sample_session_data["state"]

            # Verify database query
            mock_db.fetch_one.assert_called_once()
            call_args = mock_db.fetch_one.call_args[0][0]
            assert "SELECT * FROM sessions WHERE id = $1" in call_args

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, session_manager):
        """Test session retrieval when not found."""
        # Setup
        session_id = str(uuid.uuid4())

        # Mock database to return None
        with patch('app.agents.sessions.db') as mock_db:
            mock_db.fetch_one = AsyncMock(return_value=None)

            # Execute
            session = await session_manager.get_session(session_id)

            # Verify
            assert session is None

    @pytest.mark.asyncio
    async def test_get_session_database_error(self, session_manager, caplog):
        """Test session retrieval handles database errors."""
        # Setup
        session_id = str(uuid.uuid4())

        # Mock database to raise exception
        with patch('app.agents.sessions.db') as mock_db:
            mock_db.fetch_one = AsyncMock(side_effect=Exception("Database error"))

            # Execute
            session = await session_manager.get_session(session_id)

            # Verify
            assert session is None
            assert "Failed to get session" in caplog.text

    @pytest.mark.asyncio
    async def test_list_sessions(self, session_manager, sample_session_data):
        """Test listing sessions."""
        # Setup
        agent_id = sample_session_data["agent_id"]

        # Mock database to return multiple sessions
        multiple_sessions = [sample_session_data.copy() for _ in range(3)]
        for i, sess in enumerate(multiple_sessions):
            sess["id"] = str(uuid.uuid4())

        with patch('app.agents.sessions.db') as mock_db:
            mock_db.fetch_all = AsyncMock(return_value=multiple_sessions)

            # Execute
            sessions = await session_manager.list_sessions(agent_id=agent_id)

            # Verify
            assert len(sessions) == 3
            mock_db.fetch_all.assert_called_once()
            call_args = mock_db.fetch_all.call_args[0][0]
            assert "WHERE agent_id = $1" in call_args

    @pytest.mark.asyncio
    async def test_list_sessions_with_state_filter(self, session_manager):
        """Test listing sessions with state filter."""
        # Setup
        agent_id = str(uuid.uuid4())
        state = SessionStatus.ACTIVE

        # Mock database
        with patch('app.agents.sessions.db') as mock_db:
            mock_db.fetch_all = AsyncMock(return_value=[])

            # Execute
            sessions = await session_manager.list_sessions(
                agent_id=agent_id,
                state=state
            )

            # Verify
            mock_db.fetch_all.assert_called_once()
            call_args = mock_db.fetch_all.call_args[0][0]
            assert "AND state = $2" in call_args

    @pytest.mark.asyncio
    async def test_add_message_success(self, session_manager, sample_session_data):
        """Test adding message to session."""
        # Setup
        session_id = sample_session_data["id"]
        role = "user"
        content = "Test message content"
        metadata = {"source": "test"}

        # Mock get_session to return a session
        mock_session = Mock()
        mock_session.id = session_id
        mock_session.agent_id = sample_session_data["agent_id"]
        mock_session.add_message = AsyncMock()

        with patch.object(session_manager, 'get_session', AsyncMock(return_value=mock_session)):
            # Mock database insert
            with patch('app.agents.sessions.db') as mock_db:
                mock_db.fetch_one = AsyncMock(return_value={"id": uuid.uuid4()})

                # Execute
                message = await session_manager.add_message(
                    session_id=session_id,
                    role=role,
                    content=content,
                    metadata=metadata
                )

                # Verify
                assert message is not None
                assert message.role == role
                assert message.content == content
                mock_session.add_message.assert_called_once()

                # Verify database query (checking for $2 syntax fix)
                mock_db.fetch_one.assert_called_once()
                call_args = mock_db.fetch_one.call_args[0][0]
                assert "INSERT INTO session_messages" in call_args
                # Check parameter numbering is correct
                assert "$1" in call_args
                assert "$2" in call_args
                assert "$3" in call_args

    @pytest.mark.asyncio
    async def test_add_message_session_not_found(self, session_manager):
        """Test adding message to non-existent session."""
        # Setup
        session_id = str(uuid.uuid4())

        # Mock get_session to return None
        with patch.object(session_manager, 'get_session', AsyncMock(return_value=None)):
            # Execute & Verify
            with pytest.raises(ValueError, match="Session not found"):
                await session_manager.add_message(
                    session_id=session_id,
                    role="user",
                    content="Test message"
                )

    @pytest.mark.asyncio
    async def test_get_messages(self, session_manager, sample_session_data):
        """Test retrieving session messages."""
        # Setup
        session_id = sample_session_data["id"]

        # Mock database to return messages
        sample_messages = [
            {
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "role": "user",
                "content": "Hello",
                "metadata": {},
                "created_at": datetime.now()
            },
            {
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "role": "assistant",
                "content": "Hi there!",
                "metadata": {},
                "created_at": datetime.now()
            }
        ]

        with patch('app.agents.sessions.db') as mock_db:
            mock_db.fetch_all = AsyncMock(return_value=sample_messages)

            # Execute
            messages = await session_manager.get_messages(
                session_id=session_id,
                limit=10
            )

            # Verify
            assert len(messages) == 2
            mock_db.fetch_all.assert_called_once()
            call_args = mock_db.fetch_all.call_args[0][0]
            assert "WHERE session_id = $1" in call_args
            assert "ORDER BY created_at ASC" in call_args
            assert "LIMIT 10" in call_args or "LIMIT $2" in call_args

    @pytest.mark.asyncio
    async def test_end_session_success(self, session_manager, sample_session_data):
        """Test successful session ending."""
        # Setup
        session_id = sample_session_data["id"]

        # Mock get_session to return a session
        mock_session = Mock()
        mock_session.id = session_id
        mock_session.end = AsyncMock()

        with patch.object(session_manager, 'get_session', AsyncMock(return_value=mock_session)):
            # Mock database update
            with patch('app.agents.sessions.db') as mock_db:
                mock_db.execute = AsyncMock()

                # Execute
                success = await session_manager.end_session(session_id)

                # Verify
                assert success is True
                mock_session.end.assert_called_once()
                mock_db.execute.assert_called_once()
                call_args = mock_db.execute.call_args[0][0]
                assert "UPDATE sessions" in call_args
                assert "state = 'ended'" in call_args or "state = $2" in call_args
                assert "ended_at = NOW()" in call_args or "ended_at = $3" in call_args

    @pytest.mark.asyncio
    async def test_end_session_not_found(self, session_manager):
        """Test ending non-existent session."""
        # Setup
        session_id = str(uuid.uuid4())

        # Mock get_session to return None
        with patch.object(session_manager, 'get_session', AsyncMock(return_value=None)):
            # Execute
            success = await session_manager.end_session(session_id)

            # Verify
            assert success is False

    @pytest.mark.asyncio
    async def test_update_session_context(self, session_manager, sample_session_data):
        """Test updating session context."""
        # Setup
        session_id = sample_session_data["id"]
        new_context = {"topic": "updated", "priority": "high"}

        # Mock database update
        with patch('app.agents.sessions.db') as mock_db:
            mock_db.execute = AsyncMock()

            # Execute
            success = await session_manager.update_session_context(
                session_id=session_id,
                context=new_context
            )

            # Verify
            assert success is True
            mock_db.execute.assert_called_once()
            call_args = mock_db.execute.call_args[0][0]
            assert "UPDATE sessions" in call_args
            assert "context = $1" in call_args or "context = $2" in call_args
            assert "updated_at = NOW()" in call_args

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, session_manager):
        """Test cleaning up expired sessions."""
        # Mock database operations
        with patch('app.agents.sessions.db') as mock_db:
            # Mock finding expired sessions
            expired_sessions = [
                {"id": str(uuid.uuid4()), "agent_id": str(uuid.uuid4())}
                for _ in range(3)
            ]
            mock_db.fetch_all = AsyncMock(return_value=expired_sessions)
            mock_db.execute = AsyncMock()

            # Execute
            cleaned_count = await session_manager.cleanup_expired_sessions()

            # Verify
            assert cleaned_count == 3
            # Should call to find expired sessions
            mock_db.fetch_all.assert_called_once()
            find_call_args = mock_db.fetch_all.call_args[0][0]
            assert "WHERE state = 'active'" in find_call_args
            assert "AND created_at <" in find_call_args

            # Should call to update each expired session
            assert mock_db.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_get_session_stats(self, session_manager):
        """Test getting session statistics."""
        # Setup
        agent_id = str(uuid.uuid4())

        # Mock database queries
        with patch('app.agents.sessions.db') as mock_db:
            mock_db.fetch_one = AsyncMock(side_effect=[
                {"count": 5, "avg_duration": 300.5},  # active sessions
                {"count": 10, "avg_duration": 1200.0},  # total sessions
                {"count": 150}  # total messages
            ])

            # Execute
            stats = await session_manager.get_session_stats(agent_id)

            # Verify
            assert "active_sessions" in stats
            assert "total_sessions" in stats
            assert "total_messages" in stats
            assert "avg_session_duration" in stats
            assert stats["active_sessions"] == 5
            assert stats["total_sessions"] == 10
            assert stats["total_messages"] == 150

            # Verify database queries
            assert mock_db.fetch_one.call_count == 3