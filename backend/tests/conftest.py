"""
Shared pytest fixtures for testing the RAG system
"""
import pytest
import tempfile
import shutil
import os
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typing import Generator

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rag_system import RAGSystem
from fixtures.mock_data import (
    MOCK_CONFIG, 
    MOCK_ANTHROPIC_RESPONSE_SIMPLE,
    MOCK_SEARCH_RESULTS_SUCCESS,
    create_mock_vector_store,
    create_mock_anthropic_client,
)


@pytest.fixture(scope="function")
def temp_directory() -> Generator[str, None, None]:
    """Create a temporary directory for test files"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture(scope="function")
def test_config(temp_directory):
    """Test configuration with temporary directory"""
    return type('Config', (), {
        'ANTHROPIC_API_KEY': 'test-api-key',
        'ANTHROPIC_MODEL': 'claude-3-sonnet-20241022',
        'EMBEDDING_MODEL': 'all-MiniLM-L6-v2',
        'CHUNK_SIZE': 100,
        'CHUNK_OVERLAP': 20,
        'MAX_RESULTS': 3,
        'MAX_HISTORY': 2,
        'CHROMA_PATH': os.path.join(temp_directory, 'test_chroma')
    })()


@pytest.fixture(scope="function")
def mock_rag_system(test_config):
    """Mock RAG system with controlled responses"""
    with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
        mock_anthropic.return_value = create_mock_anthropic_client()
        
        rag_system = RAGSystem(test_config)
        
        # Mock the vector store to return controlled results
        rag_system.vector_store = create_mock_vector_store()
        
        # Mock common methods
        rag_system.query = MagicMock(return_value=("Test response", ["Test source"]))
        rag_system.get_course_analytics = MagicMock(return_value={
            "total_courses": 2,
            "course_titles": ["Test Course 1", "Test Course 2"]
        })
        rag_system.session_manager.create_session = MagicMock(return_value="test-session-123")
        rag_system.session_manager.clear_session = MagicMock()
        
        yield rag_system


@pytest.fixture(scope="function")
def test_app():
    """Create a test FastAPI app without static file mounting"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from pydantic import BaseModel
    from typing import List, Optional, Union, Dict, Any
    
    # Create test app
    app = FastAPI(title="Test RAG System", root_path="")
    
    # Add middleware
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # Pydantic models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Union[str, Dict[str, Any]]]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    class ClearSessionRequest(BaseModel):
        session_id: Optional[str] = None
    
    # Mock RAG system for the test app
    mock_rag = MagicMock()
    mock_rag.query.return_value = ("Test response", ["Test source"])
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Test Course 1", "Test Course 2"]
    }
    mock_rag.session_manager.create_session.return_value = "test-session-123"
    mock_rag.session_manager.clear_session.return_value = None
    
    # API Endpoints
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag.session_manager.create_session()
            
            answer, sources = mock_rag.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/clear-session")
    async def clear_session(request: ClearSessionRequest):
        try:
            if request.session_id:
                mock_rag.session_manager.clear_session(request.session_id)
            
            new_session_id = mock_rag.session_manager.create_session()
            return {"session_id": new_session_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/")
    async def read_root():
        return {"message": "Test API is running"}
    
    # Store mock_rag for access in tests
    app.state.mock_rag = mock_rag
    
    return app


@pytest.fixture(scope="function")
def client(test_app):
    """Test client for the FastAPI app"""
    return TestClient(test_app)


@pytest.fixture(scope="function")
def sample_test_data():
    """Sample test data for API tests"""
    return {
        "valid_query_request": {
            "query": "What is machine learning?",
            "session_id": "test-session-123"
        },
        "query_without_session": {
            "query": "What is AI?"
        },
        "clear_session_request": {
            "session_id": "test-session-123"
        },
        "empty_clear_session_request": {},
        "expected_course_stats": {
            "total_courses": 2,
            "course_titles": ["Test Course 1", "Test Course 2"]
        },
        "expected_query_response": {
            "answer": "Test response",
            "sources": ["Test source"],
            "session_id": "test-session-123"
        }
    }


@pytest.fixture(scope="function")
def course_test_document(temp_directory):
    """Create a test course document for integration tests"""
    docs_dir = os.path.join(temp_directory, 'docs')
    os.makedirs(docs_dir)
    
    test_file = os.path.join(docs_dir, 'test_course.txt')
    with open(test_file, 'w') as f:
        f.write("""Course Title: Test API Course
Course Link: https://example.com/test-api-course
Course Instructor: API Test Instructor

Lesson 1: API Testing Fundamentals
Lesson Link: https://example.com/test-api-course/lesson1
API testing is crucial for ensuring that your web services work correctly. It involves testing the communication between different software components through their application programming interfaces.

Lesson 2: FastAPI Testing Patterns
Lesson Link: https://example.com/test-api-course/lesson2
FastAPI provides excellent testing capabilities with TestClient. You can test your API endpoints by making HTTP requests and asserting on the responses.""")
    
    return test_file


@pytest.fixture(autouse=True)
def clean_environment():
    """Clean up environment variables and state before each test"""
    # Store original environment
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ['ANTHROPIC_API_KEY'] = 'test-key'
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)