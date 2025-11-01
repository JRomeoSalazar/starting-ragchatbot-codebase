"""Tests for CourseSearchTool.execute() method"""

from unittest.mock import MagicMock

import pytest
from search_tools import CourseOutlineTool, CourseSearchTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchTool:
    """Test suite for CourseSearchTool"""

    def test_execute_query_only(self, mock_vector_store, sample_search_results):
        """Test basic search without any filters"""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="What is MCP?")

        # Verify VectorStore.search was called with correct parameters
        mock_vector_store.search.assert_called_once_with(
            query="What is MCP?", course_name=None, lesson_number=None
        )

        # Verify result contains formatted content
        assert result is not None
        assert "Introduction to MCP" in result
        assert "Lesson 0" in result or "content:" in result.lower()

    def test_execute_with_course_filter(self, mock_vector_store, sample_search_results):
        """Test search filtered by course name"""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="What is MCP?", course_name="Introduction to MCP")

        # Verify course filter was passed
        mock_vector_store.search.assert_called_once_with(
            query="What is MCP?", course_name="Introduction to MCP", lesson_number=None
        )

        assert result is not None
        assert "Introduction to MCP" in result

    def test_execute_with_lesson_filter(self, mock_vector_store, sample_search_results):
        """Test search filtered by lesson number"""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="Getting started", lesson_number=1)

        # Verify lesson filter was passed
        mock_vector_store.search.assert_called_once_with(
            query="Getting started", course_name=None, lesson_number=1
        )

        assert result is not None

    def test_execute_with_both_filters(self, mock_vector_store, sample_search_results):
        """Test search with both course and lesson filters"""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(
            query="Advanced concepts",
            course_name="Introduction to MCP",
            lesson_number=2,
        )

        # Verify both filters were passed
        mock_vector_store.search.assert_called_once_with(
            query="Advanced concepts",
            course_name="Introduction to MCP",
            lesson_number=2,
        )

        assert result is not None

    def test_execute_empty_results(self, mock_vector_store, empty_search_results):
        """Test handling of empty search results"""
        tool = CourseSearchTool(mock_vector_store)

        # Mock empty results
        mock_vector_store.search.return_value = empty_search_results

        result = tool.execute(query="NonExistentTopic")

        # Should return a "not found" message
        assert "No relevant content found" in result

    def test_execute_empty_results_with_filters(
        self, mock_vector_store, empty_search_results
    ):
        """Test empty results message includes filter information"""
        tool = CourseSearchTool(mock_vector_store)

        # Mock empty results
        mock_vector_store.search.return_value = empty_search_results

        result = tool.execute(
            query="NonExistentTopic", course_name="MCP", lesson_number=5
        )

        # Should mention the filters in the message
        assert "No relevant content found" in result
        assert "MCP" in result or "lesson" in result.lower()

    def test_execute_error_handling(self, mock_vector_store, error_search_results):
        """Test error propagation from VectorStore"""
        tool = CourseSearchTool(mock_vector_store)

        # Mock error results
        mock_vector_store.search.return_value = error_search_results

        result = tool.execute(query="test", course_name="NonExistent")

        # Should return the error message
        assert "No course found matching 'NonExistent'" in result

    def test_source_tracking(self, mock_vector_store, sample_search_results):
        """Test that sources are properly tracked in last_sources"""
        tool = CourseSearchTool(mock_vector_store)

        # Execute search
        result = tool.execute(query="MCP basics", course_name="Introduction to MCP")

        # Verify last_sources was populated
        assert hasattr(tool, "last_sources")
        assert len(tool.last_sources) > 0

        # Check source structure
        for source in tool.last_sources:
            assert "text" in source
            assert "url" in source

    def test_format_results_with_course_and_lesson(self, mock_vector_store):
        """Test result formatting includes course title and lesson number"""
        tool = CourseSearchTool(mock_vector_store)

        # Create specific search results
        results = SearchResults(
            documents=["This is lesson 1 content about MCP."],
            metadata=[
                {
                    "course_title": "Introduction to MCP",
                    "lesson_number": 1,
                    "chunk_index": 0,
                }
            ],
            distances=[0.1],
            error=None,
        )

        mock_vector_store.search.return_value = results

        result = tool.execute(query="MCP")

        # Verify formatting includes course and lesson
        assert "[Introduction to MCP - Lesson 1]" in result
        assert "This is lesson 1 content" in result


class TestToolManager:
    """Test suite for ToolManager"""

    def test_register_tool(self, mock_vector_store):
        """Test tool registration"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)

        manager.register_tool(tool)

        # Verify tool was registered
        assert "search_course_content" in manager.tools

    def test_get_tool_definitions(self, mock_vector_store):
        """Test getting all tool definitions"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        definitions = manager.get_tool_definitions()

        assert len(definitions) >= 1
        assert any(d["name"] == "search_course_content" for d in definitions)

    def test_execute_tool(self, mock_vector_store, sample_search_results):
        """Test executing a tool by name"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        result = manager.execute_tool("search_course_content", query="MCP basics")

        assert result is not None
        assert isinstance(result, str)

    def test_execute_nonexistent_tool(self, mock_vector_store):
        """Test executing a tool that doesn't exist"""
        manager = ToolManager()

        result = manager.execute_tool("nonexistent_tool", query="test")

        assert "not found" in result.lower()

    def test_get_last_sources(self, mock_vector_store, sample_search_results):
        """Test retrieving sources from last search"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        # Execute a search to populate sources
        manager.execute_tool("search_course_content", query="MCP")

        sources = manager.get_last_sources()

        assert isinstance(sources, list)

    def test_reset_sources(self, mock_vector_store, sample_search_results):
        """Test resetting sources after retrieval"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        # Execute search and verify sources exist
        manager.execute_tool("search_course_content", query="MCP")
        sources_before = manager.get_last_sources()
        assert len(sources_before) > 0

        # Reset sources
        manager.reset_sources()

        # Verify sources are cleared
        sources_after = manager.get_last_sources()
        assert len(sources_after) == 0


class TestCourseOutlineTool:
    """Test suite for CourseOutlineTool"""

    def test_execute_valid_course(self, mock_vector_store):
        """Test getting outline for existing course"""
        tool = CourseOutlineTool(mock_vector_store)

        result = tool.execute(course_name="MCP")

        # Verify get_course_outline was called
        mock_vector_store.get_course_outline.assert_called_once_with("MCP")

        # Verify result contains course information
        assert "Introduction to MCP" in result
        assert "Lesson" in result

    def test_execute_nonexistent_course(self, mock_vector_store):
        """Test getting outline for non-existent course"""
        tool = CourseOutlineTool(mock_vector_store)

        # Mock no course found
        mock_vector_store.get_course_outline.return_value = None

        result = tool.execute(course_name="NonExistent")

        assert "No course found" in result
        assert "NonExistent" in result
