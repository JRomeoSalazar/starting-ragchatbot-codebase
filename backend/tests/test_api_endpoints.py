"""Tests for FastAPI endpoints"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.api
class TestQueryEndpoint:
    """Test suite for /api/query endpoint"""

    def test_query_with_session_id(self, test_client, sample_query_request, mock_rag_system):
        """Test query endpoint with provided session_id"""
        response = test_client.post("/api/query", json=sample_query_request)

        # Verify response status
        assert response.status_code == 200

        # Verify response structure
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Verify content
        assert data["answer"] == "This is a test answer from the RAG system."
        assert data["session_id"] == "session_1"
        assert len(data["sources"]) == 1
        assert data["sources"][0]["text"] == "Introduction to MCP - Lesson 1"
        assert data["sources"][0]["url"] == "https://example.com/lesson1"

        # Verify RAG system was called correctly
        mock_rag_system.query.assert_called_once_with("What is MCP?", "session_1")

    def test_query_without_session_id(self, test_client, sample_query_request_no_session, mock_rag_system):
        """Test query endpoint creates session when not provided"""
        response = test_client.post("/api/query", json=sample_query_request_no_session)

        # Verify response status
        assert response.status_code == 200

        # Verify session was created
        mock_rag_system.session_manager.create_session.assert_called_once()

        # Verify response structure
        data = response.json()
        assert data["session_id"] == "session_1"
        assert "answer" in data
        assert "sources" in data

    def test_query_with_empty_query(self, test_client):
        """Test query endpoint with empty query string"""
        response = test_client.post("/api/query", json={"query": ""})

        # Should still process (validation happens at RAG level, not endpoint)
        assert response.status_code == 200

    def test_query_missing_query_field(self, test_client):
        """Test query endpoint with missing query field"""
        response = test_client.post("/api/query", json={"session_id": "session_1"})

        # Should return 422 for validation error
        assert response.status_code == 422

    def test_query_invalid_json(self, test_client):
        """Test query endpoint with invalid JSON"""
        response = test_client.post(
            "/api/query",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        # Should return 422 for invalid JSON
        assert response.status_code == 422

    def test_query_rag_system_error(self, test_client, sample_query_request, mock_rag_system):
        """Test query endpoint when RAG system raises an error"""
        # Configure mock to raise exception
        mock_rag_system.query.side_effect = Exception("Database connection failed")

        response = test_client.post("/api/query", json=sample_query_request)

        # Should return 500 for internal server error
        assert response.status_code == 500
        assert "Database connection failed" in response.json()["detail"]

    def test_query_response_types(self, test_client, sample_query_request):
        """Test that response fields have correct types"""
        response = test_client.post("/api/query", json=sample_query_request)
        data = response.json()

        # Verify types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Verify source structure
        if data["sources"]:
            assert isinstance(data["sources"][0]["text"], str)
            assert data["sources"][0]["url"] is None or isinstance(data["sources"][0]["url"], str)

    def test_query_with_special_characters(self, test_client, mock_rag_system):
        """Test query with special characters and unicode"""
        special_query = {
            "query": "What is MCP? 🤖 How does it work with côde?",
            "session_id": "session_1"
        }

        response = test_client.post("/api/query", json=special_query)

        assert response.status_code == 200
        mock_rag_system.query.assert_called_once_with(
            "What is MCP? 🤖 How does it work with côde?",
            "session_1"
        )

    def test_query_long_text(self, test_client, mock_rag_system):
        """Test query with very long text"""
        long_query = {
            "query": "A" * 10000,  # 10,000 character query
            "session_id": "session_1"
        }

        response = test_client.post("/api/query", json=long_query)

        # Should process long queries
        assert response.status_code == 200


@pytest.mark.api
class TestCoursesEndpoint:
    """Test suite for /api/courses endpoint"""

    def test_get_courses_success(self, test_client, mock_rag_system):
        """Test successful retrieval of course statistics"""
        response = test_client.get("/api/courses")

        # Verify response status
        assert response.status_code == 200

        # Verify response structure
        data = response.json()
        assert "total_courses" in data
        assert "course_titles" in data

        # Verify content
        assert data["total_courses"] == 1
        assert data["course_titles"] == ["Introduction to MCP"]

        # Verify RAG system was called
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_get_courses_empty(self, test_client, mock_rag_system):
        """Test course statistics when no courses exist"""
        # Configure mock to return empty data
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_get_courses_multiple(self, test_client, mock_rag_system):
        """Test course statistics with multiple courses"""
        # Configure mock to return multiple courses
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": [
                "Introduction to MCP",
                "Advanced MCP Patterns",
                "MCP Best Practices"
            ]
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 3
        assert len(data["course_titles"]) == 3

    def test_get_courses_error(self, test_client, mock_rag_system):
        """Test course endpoint when analytics raises an error"""
        # Configure mock to raise exception
        mock_rag_system.get_course_analytics.side_effect = Exception("Vector store error")

        response = test_client.get("/api/courses")

        # Should return 500 for internal server error
        assert response.status_code == 500
        assert "Vector store error" in response.json()["detail"]

    def test_get_courses_response_types(self, test_client):
        """Test that response fields have correct types"""
        response = test_client.get("/api/courses")
        data = response.json()

        # Verify types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        for title in data["course_titles"]:
            assert isinstance(title, str)


@pytest.mark.api
class TestClearSessionEndpoint:
    """Test suite for /api/clear-session endpoint"""

    def test_clear_session_success(self, test_client, mock_rag_system):
        """Test successful session clearing"""
        request_data = {"session_id": "session_1"}
        response = test_client.post("/api/clear-session", json=request_data)

        # Verify response status
        assert response.status_code == 200

        # Verify response structure
        data = response.json()
        assert "success" in data
        assert "message" in data

        # Verify content
        assert data["success"] is True
        assert "session_1" in data["message"]
        assert "cleared successfully" in data["message"]

        # Verify session manager was called
        mock_rag_system.session_manager.clear_session.assert_called_once_with("session_1")

    def test_clear_session_missing_id(self, test_client):
        """Test clear session without session_id"""
        response = test_client.post("/api/clear-session", json={})

        # Should return 422 for validation error
        assert response.status_code == 422

    def test_clear_session_error(self, test_client, mock_rag_system):
        """Test clear session when session manager raises error"""
        # Configure mock to raise exception
        mock_rag_system.session_manager.clear_session.side_effect = Exception("Session not found")

        request_data = {"session_id": "nonexistent_session"}
        response = test_client.post("/api/clear-session", json=request_data)

        # Should return 500 for internal server error
        assert response.status_code == 500
        assert "Session not found" in response.json()["detail"]

    def test_clear_multiple_sessions(self, test_client, mock_rag_system):
        """Test clearing multiple sessions sequentially"""
        sessions = ["session_1", "session_2", "session_3"]

        for session_id in sessions:
            request_data = {"session_id": session_id}
            response = test_client.post("/api/clear-session", json=request_data)

            assert response.status_code == 200
            assert response.json()["success"] is True

        # Verify all sessions were cleared
        assert mock_rag_system.session_manager.clear_session.call_count == 3


@pytest.mark.api
class TestRootEndpoint:
    """Test suite for / root endpoint"""

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns basic info"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "RAG System API"


@pytest.mark.api
class TestAPIIntegration:
    """Integration tests for API endpoint interactions"""

    def test_full_query_workflow(self, test_client, mock_rag_system):
        """Test complete workflow: query without session, then with session"""
        # First query without session
        response1 = test_client.post("/api/query", json={"query": "What is MCP?"})
        assert response1.status_code == 200
        session_id = response1.json()["session_id"]

        # Second query with same session
        response2 = test_client.post("/api/query", json={
            "query": "Tell me more",
            "session_id": session_id
        })
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

        # Verify RAG system was called twice
        assert mock_rag_system.query.call_count == 2

    def test_query_and_clear_workflow(self, test_client, mock_rag_system):
        """Test workflow: create session, query, then clear session"""
        # Query to create session
        query_response = test_client.post("/api/query", json={"query": "What is MCP?"})
        session_id = query_response.json()["session_id"]

        # Clear the session
        clear_response = test_client.post("/api/clear-session", json={"session_id": session_id})
        assert clear_response.status_code == 200
        assert clear_response.json()["success"] is True

    def test_multiple_endpoint_calls(self, test_client, mock_rag_system):
        """Test calling multiple different endpoints"""
        # Get courses
        courses_response = test_client.get("/api/courses")
        assert courses_response.status_code == 200

        # Make a query
        query_response = test_client.post("/api/query", json={"query": "What is MCP?"})
        assert query_response.status_code == 200
        session_id = query_response.json()["session_id"]

        # Clear session
        clear_response = test_client.post("/api/clear-session", json={"session_id": session_id})
        assert clear_response.status_code == 200

        # Get courses again
        courses_response2 = test_client.get("/api/courses")
        assert courses_response2.status_code == 200


@pytest.mark.api
class TestAPIHeaders:
    """Test API response headers"""

    def test_content_type_headers(self, test_client):
        """Test that responses have correct content-type"""
        response = test_client.get("/api/courses")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_query_content_type(self, test_client):
        """Test query endpoint content type"""
        response = test_client.post("/api/query", json={"query": "test"})
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
