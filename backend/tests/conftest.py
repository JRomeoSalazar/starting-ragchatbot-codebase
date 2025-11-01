"""Shared test fixtures for RAG chatbot tests"""

import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock

import pytest

# Add backend directory to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from config import Config
from models import Course, CourseChunk, Lesson
from vector_store import SearchResults


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    config = Mock(spec=Config)
    config.ANTHROPIC_API_KEY = "test-api-key"
    config.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_RESULTS = 5
    config.MAX_HISTORY = 2
    config.CHROMA_PATH = "./test_chroma_db"
    return config


@pytest.fixture
def sample_course_data():
    """Sample course data for testing"""
    lessons = [
        Lesson(
            lesson_number=0,
            title="Introduction",
            lesson_link="https://example.com/lesson0",
        ),
        Lesson(
            lesson_number=1,
            title="Getting Started",
            lesson_link="https://example.com/lesson1",
        ),
        Lesson(
            lesson_number=2,
            title="Advanced Topics",
            lesson_link="https://example.com/lesson2",
        ),
    ]

    course = Course(
        title="Introduction to MCP",
        course_link="https://example.com/course",
        instructor="Test Instructor",
        lessons=lessons,
    )

    return course


@pytest.fixture
def sample_course_chunks(sample_course_data):
    """Sample course chunks for testing"""
    chunks = [
        CourseChunk(
            content="Introduction to MCP Lesson 0 content: This is the introduction to Model Context Protocol.",
            course_title=sample_course_data.title,
            lesson_number=0,
            chunk_index=0,
        ),
        CourseChunk(
            content="Introduction to MCP Lesson 1 content: Let's get started with MCP basics.",
            course_title=sample_course_data.title,
            lesson_number=1,
            chunk_index=1,
        ),
        CourseChunk(
            content="Introduction to MCP Lesson 2 content: Advanced MCP concepts and patterns.",
            course_title=sample_course_data.title,
            lesson_number=2,
            chunk_index=2,
        ),
    ]
    return chunks


@pytest.fixture
def sample_search_results(sample_course_chunks):
    """Sample SearchResults for testing"""
    results = SearchResults(
        documents=[chunk.content for chunk in sample_course_chunks],
        metadata=[
            {
                "course_title": chunk.course_title,
                "lesson_number": chunk.lesson_number,
                "chunk_index": chunk.chunk_index,
            }
            for chunk in sample_course_chunks
        ],
        distances=[0.1, 0.2, 0.3],
        error=None,
    )
    return results


@pytest.fixture
def empty_search_results():
    """Empty SearchResults for testing"""
    return SearchResults(documents=[], metadata=[], distances=[], error=None)


@pytest.fixture
def error_search_results():
    """SearchResults with error for testing"""
    return SearchResults.empty("No course found matching 'NonExistent'")


@pytest.fixture
def mock_vector_store(sample_search_results):
    """Mock VectorStore for testing"""
    mock_store = MagicMock()

    # Default behavior: return sample results
    mock_store.search.return_value = sample_search_results

    # Mock course resolution
    mock_store._resolve_course_name.return_value = "Introduction to MCP"

    # Mock lesson link retrieval
    mock_store.get_lesson_link.return_value = "https://example.com/lesson1"

    # Mock course link retrieval
    mock_store.get_course_link.return_value = "https://example.com/course"

    # Mock course outline
    mock_store.get_course_outline.return_value = {
        "title": "Introduction to MCP",
        "course_link": "https://example.com/course",
        "instructor": "Test Instructor",
        "lesson_count": 3,
        "lessons": [
            {
                "lesson_number": 0,
                "lesson_title": "Introduction",
                "lesson_link": "https://example.com/lesson0",
            },
            {
                "lesson_number": 1,
                "lesson_title": "Getting Started",
                "lesson_link": "https://example.com/lesson1",
            },
            {
                "lesson_number": 2,
                "lesson_title": "Advanced Topics",
                "lesson_link": "https://example.com/lesson2",
            },
        ],
    }

    # Mock existing course titles
    mock_store.get_existing_course_titles.return_value = ["Introduction to MCP"]
    mock_store.get_course_count.return_value = 1

    return mock_store


@pytest.fixture
def mock_anthropic_response_no_tool():
    """Mock Anthropic response without tool use"""
    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"

    # Create a mock content block with text
    mock_content = MagicMock()
    mock_content.type = "text"
    mock_content.text = "This is a direct answer from Claude."
    mock_response.content = [mock_content]

    return mock_response


@pytest.fixture
def mock_anthropic_response_with_tool():
    """Mock Anthropic response with tool use"""
    mock_response = MagicMock()
    mock_response.stop_reason = "tool_use"

    # Create mock text block
    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = "Let me search for that information."

    # Create mock tool use block
    mock_tool_block = MagicMock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.id = "tool_use_123"
    mock_tool_block.name = "search_course_content"
    mock_tool_block.input = {"query": "MCP basics", "course_name": "MCP"}

    mock_response.content = [mock_text_block, mock_tool_block]

    return mock_response


@pytest.fixture
def mock_anthropic_final_response():
    """Mock Anthropic final response after tool execution"""
    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"

    mock_content = MagicMock()
    mock_content.type = "text"
    mock_content.text = (
        "Based on the search results, MCP stands for Model Context Protocol."
    )
    mock_response.content = [mock_content]

    return mock_response


@pytest.fixture
def mock_anthropic_client(mock_anthropic_response_no_tool):
    """Mock Anthropic client for testing"""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_anthropic_response_no_tool
    return mock_client


@pytest.fixture
def mock_tool_manager():
    """Mock ToolManager for testing"""
    mock_manager = MagicMock()
    mock_manager.get_tool_definitions.return_value = [
        {
            "name": "search_course_content",
            "description": "Search course materials",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "course_name": {"type": "string"},
                    "lesson_number": {"type": "integer"},
                },
                "required": ["query"],
            },
        }
    ]
    mock_manager.execute_tool.return_value = (
        "[Introduction to MCP - Lesson 1]\nMCP basics content..."
    )
    mock_manager.get_last_sources.return_value = [
        {"text": "Introduction to MCP - Lesson 1", "url": "https://example.com/lesson1"}
    ]
    return mock_manager


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager for testing"""
    mock_manager = MagicMock()
    mock_manager.create_session.return_value = "session_1"
    mock_manager.get_conversation_history.return_value = (
        "User: Previous question\nAssistant: Previous answer"
    )
    return mock_manager
