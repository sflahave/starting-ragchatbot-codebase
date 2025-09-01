"""
API endpoint tests for the FastAPI RAG system
"""
import pytest
import json
from fastapi.testclient import TestClient


@pytest.mark.api
class TestAPIEndpoints:
    """Test suite for FastAPI API endpoints"""

    def test_root_endpoint(self, client: TestClient):
        """Test the root endpoint returns successfully"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Test API is running"

    def test_query_endpoint_with_session(self, client: TestClient, sample_test_data):
        """Test POST /api/query with session ID"""
        request_data = sample_test_data["valid_query_request"]
        
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        
        # Verify response content
        assert data["answer"] == "Test response"
        assert data["sources"] == ["Test source"]
        assert data["session_id"] == "test-session-123"

    def test_query_endpoint_without_session(self, client: TestClient, sample_test_data):
        """Test POST /api/query without session ID - should create new session"""
        request_data = sample_test_data["query_without_session"]
        
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        
        # Verify response content
        assert data["answer"] == "Test response"
        assert data["sources"] == ["Test source"]
        assert data["session_id"] == "test-session-123"  # From mock

    def test_query_endpoint_invalid_request(self, client: TestClient):
        """Test POST /api/query with invalid request data"""
        # Missing required 'query' field
        request_data = {"session_id": "test"}
        
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == 422  # Validation error

    def test_query_endpoint_empty_query(self, client: TestClient):
        """Test POST /api/query with empty query"""
        request_data = {"query": ""}
        
        response = client.post("/api/query", json=request_data)
        
        # Should still work with empty query (business logic decision)
        assert response.status_code == 200

    def test_query_endpoint_server_error(self, client: TestClient, test_app):
        """Test POST /api/query when RAG system throws exception"""
        # Configure mock to throw exception
        test_app.state.mock_rag.query.side_effect = Exception("RAG system error")
        
        request_data = {"query": "test query"}
        
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "RAG system error"

    def test_courses_endpoint_success(self, client: TestClient, sample_test_data):
        """Test GET /api/courses returns course statistics"""
        response = client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "total_courses" in data
        assert "course_titles" in data
        
        # Verify response content
        expected_stats = sample_test_data["expected_course_stats"]
        assert data["total_courses"] == expected_stats["total_courses"]
        assert data["course_titles"] == expected_stats["course_titles"]

    def test_courses_endpoint_server_error(self, client: TestClient, test_app):
        """Test GET /api/courses when RAG system throws exception"""
        # Configure mock to throw exception
        test_app.state.mock_rag.get_course_analytics.side_effect = Exception("Analytics error")
        
        response = client.get("/api/courses")
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Analytics error"

    def test_clear_session_endpoint_with_session_id(self, client: TestClient, sample_test_data):
        """Test POST /api/clear-session with existing session ID"""
        request_data = sample_test_data["clear_session_request"]
        
        response = client.post("/api/clear-session", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "session_id" in data
        assert data["session_id"] == "test-session-123"  # From mock

    def test_clear_session_endpoint_without_session_id(self, client: TestClient, sample_test_data):
        """Test POST /api/clear-session without session ID"""
        request_data = sample_test_data["empty_clear_session_request"]
        
        response = client.post("/api/clear-session", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "session_id" in data
        assert data["session_id"] == "test-session-123"  # From mock

    def test_clear_session_endpoint_server_error(self, client: TestClient, test_app):
        """Test POST /api/clear-session when session manager throws exception"""
        # Configure mock to throw exception
        test_app.state.mock_rag.session_manager.create_session.side_effect = Exception("Session error")
        
        request_data = {"session_id": "test"}
        
        response = client.post("/api/clear-session", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Session error"

    def test_cors_headers(self, client: TestClient):
        """Test that CORS headers are properly set"""
        response = client.options("/api/query")
        
        # Should allow CORS preflight
        assert response.status_code == 200

    def test_content_type_validation(self, client: TestClient):
        """Test that endpoints properly handle content-type"""
        # Test with wrong content type
        response = client.post("/api/query", 
                             data="invalid data", 
                             headers={"content-type": "text/plain"})
        
        # Should reject invalid content type
        assert response.status_code == 422


@pytest.mark.api
class TestAPIRequestValidation:
    """Test suite for API request validation"""

    def test_query_request_field_types(self, client: TestClient):
        """Test query request with wrong field types"""
        # Query should be string
        request_data = {"query": 123}
        response = client.post("/api/query", json=request_data)
        assert response.status_code == 422

        # Session ID should be string or null
        request_data = {"query": "test", "session_id": 123}
        response = client.post("/api/query", json=request_data)
        assert response.status_code == 422

    def test_clear_session_request_field_types(self, client: TestClient):
        """Test clear session request with wrong field types"""
        # Session ID should be string or null
        request_data = {"session_id": 123}
        response = client.post("/api/clear-session", json=request_data)
        assert response.status_code == 422

    def test_extra_fields_ignored(self, client: TestClient):
        """Test that extra fields in requests are handled properly"""
        request_data = {
            "query": "test query",
            "session_id": "test-session",
            "extra_field": "should be ignored"
        }
        
        response = client.post("/api/query", json=request_data)
        
        # Should still work despite extra field
        assert response.status_code == 200


@pytest.mark.api
class TestAPIResponseFormats:
    """Test suite for API response formats"""

    def test_query_response_format(self, client: TestClient):
        """Test that query response has correct format"""
        request_data = {"query": "test"}
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields are present
        required_fields = ["answer", "sources", "session_id"]
        for field in required_fields:
            assert field in data
        
        # Verify field types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

    def test_courses_response_format(self, client: TestClient):
        """Test that courses response has correct format"""
        response = client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields are present
        required_fields = ["total_courses", "course_titles"]
        for field in required_fields:
            assert field in data
        
        # Verify field types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        
        # Verify course titles are strings
        for title in data["course_titles"]:
            assert isinstance(title, str)

    def test_clear_session_response_format(self, client: TestClient):
        """Test that clear session response has correct format"""
        response = client.post("/api/clear-session", json={})
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required field is present
        assert "session_id" in data
        assert isinstance(data["session_id"], str)

    def test_error_response_format(self, client: TestClient, test_app):
        """Test that error responses have correct format"""
        # Configure mock to throw exception
        test_app.state.mock_rag.query.side_effect = Exception("Test error")
        
        request_data = {"query": "test"}
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        
        # Verify error response format
        assert "detail" in data
        assert isinstance(data["detail"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])