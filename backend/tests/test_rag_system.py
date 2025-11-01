"""Integration tests for RAGSystem end-to-end query handling"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from rag_system import RAGSystem
from search_tools import CourseOutlineTool, CourseSearchTool


class TestRAGSystemIntegration:
    """Integration tests for RAGSystem query flow"""

    @pytest.fixture
    def mock_rag_system(self, mock_config, mock_vector_store, mock_session_manager):
        """Create RAGSystem with mocked dependencies"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore", return_value=mock_vector_store),
            patch("rag_system.AIGenerator") as mock_ai_gen_class,
            patch("rag_system.SessionManager", return_value=mock_session_manager),
        ):

            # Create mock AI generator instance
            mock_ai_generator = MagicMock()
            mock_ai_gen_class.return_value = mock_ai_generator

            # Create RAG system
            rag_system = RAGSystem(mock_config)

            # Store references for test verification
            rag_system.mock_ai_generator = mock_ai_generator
            rag_system.mock_session_manager = mock_session_manager

            return rag_system

    def test_query_without_tool_use(self, mock_rag_system):
        """Test general knowledge query without tool use"""
        # Mock AI response without tool use
        mock_rag_system.mock_ai_generator.generate_response.return_value = (
            "Python is a programming language."
        )

        response, sources = mock_rag_system.query(
            "What is Python?", session_id="session_1"
        )

        # Verify response
        assert response == "Python is a programming language."

        # Verify AI generator was called with correct parameters
        mock_rag_system.mock_ai_generator.generate_response.assert_called_once()
        call_kwargs = mock_rag_system.mock_ai_generator.generate_response.call_args[1]

        # Verify tools were provided
        assert call_kwargs["tools"] is not None
        assert call_kwargs["tool_manager"] is not None

        # Sources should be empty for non-tool queries
        assert isinstance(sources, list)

    def test_query_with_tool_use(self, mock_rag_system, sample_search_results):
        """Test course content query that triggers tool use"""
        # Mock AI response after tool use
        mock_rag_system.mock_ai_generator.generate_response.return_value = (
            "MCP is Model Context Protocol."
        )

        # Mock sources from tool
        mock_rag_system.tool_manager.get_last_sources = MagicMock(
            return_value=[
                {
                    "text": "Introduction to MCP - Lesson 1",
                    "url": "https://example.com/lesson1",
                }
            ]
        )

        response, sources = mock_rag_system.query(
            "What is MCP?", session_id="session_1"
        )

        # Verify response
        assert response == "MCP is Model Context Protocol."

        # Verify AI generator was called with tools
        mock_rag_system.mock_ai_generator.generate_response.assert_called_once()
        call_kwargs = mock_rag_system.mock_ai_generator.generate_response.call_args[1]
        assert (
            call_kwargs["tools"] == mock_rag_system.tool_manager.get_tool_definitions()
        )
        assert call_kwargs["tool_manager"] == mock_rag_system.tool_manager

        # Verify sources were retrieved
        assert len(sources) > 0
        assert sources[0]["text"] == "Introduction to MCP - Lesson 1"

    def test_sources_tracking(self, mock_rag_system):
        """Test that sources are properly tracked and retrieved"""
        mock_rag_system.mock_ai_generator.generate_response.return_value = (
            "Answer based on course."
        )

        # Mock last_sources from search tool
        expected_sources = [
            {"text": "Course A - Lesson 1", "url": "https://example.com/a1"},
            {"text": "Course B - Lesson 2", "url": "https://example.com/b2"},
        ]
        mock_rag_system.tool_manager.get_last_sources = MagicMock(
            return_value=expected_sources
        )

        response, sources = mock_rag_system.query("Test query", session_id="session_1")

        # Verify sources match expected
        assert sources == expected_sources

        # Verify get_last_sources was called
        mock_rag_system.tool_manager.get_last_sources.assert_called_once()

    def test_sources_reset(self, mock_rag_system):
        """Test that sources are reset after retrieval"""
        mock_rag_system.mock_ai_generator.generate_response.return_value = "Answer"

        # Mock sources
        mock_rag_system.tool_manager.get_last_sources = MagicMock(
            return_value=[{"text": "Source 1", "url": "http://example.com"}]
        )
        mock_rag_system.tool_manager.reset_sources = MagicMock()

        response, sources = mock_rag_system.query("Query", session_id="session_1")

        # Verify reset_sources was called after retrieval
        mock_rag_system.tool_manager.reset_sources.assert_called_once()

    def test_conversation_history(self, mock_rag_system):
        """Test conversation history is passed to AI generator"""
        session_id = "session_1"

        # Mock history retrieval
        mock_rag_system.mock_session_manager.get_conversation_history.return_value = (
            "User: Previous question\nAssistant: Previous answer"
        )

        mock_rag_system.mock_ai_generator.generate_response.return_value = (
            "Follow-up answer"
        )

        response, sources = mock_rag_system.query(
            "Follow-up question", session_id=session_id
        )

        # Verify conversation history was retrieved
        mock_rag_system.mock_session_manager.get_conversation_history.assert_called_once_with(
            session_id
        )

        # Verify history was passed to AI generator
        call_kwargs = mock_rag_system.mock_ai_generator.generate_response.call_args[1]
        assert (
            call_kwargs["conversation_history"]
            == "User: Previous question\nAssistant: Previous answer"
        )

        # Verify exchange was added to history
        mock_rag_system.mock_session_manager.add_exchange.assert_called_once_with(
            session_id,
            "Answer this question about course materials: Follow-up question",
            "Follow-up answer",
        )

    def test_query_without_session(self, mock_rag_system):
        """Test query without session ID (no history)"""
        mock_rag_system.mock_ai_generator.generate_response.return_value = "Answer"

        response, sources = mock_rag_system.query("Query", session_id=None)

        # Verify no history was retrieved
        mock_rag_system.mock_session_manager.get_conversation_history.assert_not_called()

        # Verify AI generator received None for history
        call_kwargs = mock_rag_system.mock_ai_generator.generate_response.call_args[1]
        assert call_kwargs["conversation_history"] is None

        # Verify no exchange was added to history
        mock_rag_system.mock_session_manager.add_exchange.assert_not_called()

    def test_tool_manager_integration(self, mock_rag_system):
        """Test that tools are properly registered with ToolManager"""
        # Verify tools were registered
        assert "search_course_content" in mock_rag_system.tool_manager.tools
        assert "get_course_outline" in mock_rag_system.tool_manager.tools

        # Verify search tool has vector store reference
        search_tool = mock_rag_system.tool_manager.tools["search_course_content"]
        assert hasattr(search_tool, "store")

        # Verify outline tool has vector store reference
        outline_tool = mock_rag_system.tool_manager.tools["get_course_outline"]
        assert hasattr(outline_tool, "store")

    def test_error_propagation(self, mock_rag_system):
        """Test that errors from AI generator are propagated"""
        # Mock AI generator raising an exception
        mock_rag_system.mock_ai_generator.generate_response.side_effect = Exception(
            "API Error"
        )

        # Verify exception is raised
        with pytest.raises(Exception) as exc_info:
            mock_rag_system.query("Test query", session_id="session_1")

        assert "API Error" in str(exc_info.value)

    def test_query_prompt_format(self, mock_rag_system):
        """Test that query is formatted correctly for AI"""
        mock_rag_system.mock_ai_generator.generate_response.return_value = "Answer"

        mock_rag_system.query("What is MCP?", session_id=None)

        # Verify query was formatted with instruction
        call_kwargs = mock_rag_system.mock_ai_generator.generate_response.call_args[1]
        assert "Answer this question about course materials:" in call_kwargs["query"]
        assert "What is MCP?" in call_kwargs["query"]

    def test_multiple_queries_same_session(self, mock_rag_system):
        """Test multiple queries in the same session"""
        session_id = "session_1"

        # First query
        mock_rag_system.mock_ai_generator.generate_response.return_value = (
            "First answer"
        )
        response1, sources1 = mock_rag_system.query(
            "First question", session_id=session_id
        )

        # Mock history for second query
        mock_rag_system.mock_session_manager.get_conversation_history.return_value = (
            "User: First question\nAssistant: First answer"
        )

        # Second query
        mock_rag_system.mock_ai_generator.generate_response.return_value = (
            "Second answer"
        )
        response2, sources2 = mock_rag_system.query(
            "Second question", session_id=session_id
        )

        # Verify both exchanges were added
        assert mock_rag_system.mock_session_manager.add_exchange.call_count == 2

        # Verify history was retrieved for second query
        assert (
            mock_rag_system.mock_session_manager.get_conversation_history.call_count
            == 2
        )


class TestRAGSystemCourseManagement:
    """Tests for course document processing"""

    @pytest.fixture
    def mock_rag_system_with_processor(self, mock_config, mock_vector_store):
        """Create RAGSystem with mocked document processor"""
        with (
            patch("rag_system.DocumentProcessor") as mock_doc_proc_class,
            patch("rag_system.VectorStore", return_value=mock_vector_store),
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
        ):

            # Create mock document processor instance
            mock_doc_processor = MagicMock()
            mock_doc_proc_class.return_value = mock_doc_processor

            # Create RAG system
            rag_system = RAGSystem(mock_config)
            rag_system.mock_doc_processor = mock_doc_processor

            return rag_system

    def test_add_course_document(
        self, mock_rag_system_with_processor, sample_course_data, sample_course_chunks
    ):
        """Test adding a single course document"""
        # Mock document processing
        mock_rag_system_with_processor.mock_doc_processor.process_course_document.return_value = (
            sample_course_data,
            sample_course_chunks,
        )

        course, chunk_count = mock_rag_system_with_processor.add_course_document(
            "/path/to/course.txt"
        )

        # Verify document was processed
        mock_rag_system_with_processor.mock_doc_processor.process_course_document.assert_called_once_with(
            "/path/to/course.txt"
        )

        # Verify course metadata was added
        mock_rag_system_with_processor.vector_store.add_course_metadata.assert_called_once_with(
            sample_course_data
        )

        # Verify course content was added
        mock_rag_system_with_processor.vector_store.add_course_content.assert_called_once_with(
            sample_course_chunks
        )

        # Verify return values
        assert course.title == sample_course_data.title
        assert chunk_count == len(sample_course_chunks)

    def test_get_course_analytics(self, mock_rag_system_with_processor):
        """Test retrieving course analytics"""
        # Mock vector store methods
        mock_rag_system_with_processor.vector_store.get_course_count.return_value = 3
        mock_rag_system_with_processor.vector_store.get_existing_course_titles.return_value = [
            "Course A",
            "Course B",
            "Course C",
        ]

        analytics = mock_rag_system_with_processor.get_course_analytics()

        # Verify analytics structure
        assert analytics["total_courses"] == 3
        assert len(analytics["course_titles"]) == 3
        assert "Course A" in analytics["course_titles"]
