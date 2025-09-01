"""
Integration tests for RAG system end-to-end functionality
"""

import os
import shutil
import sys
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rag_system import RAGSystem
from tests.fixtures.mock_data import MOCK_ANTHROPIC_RESPONSE_SIMPLE, MOCK_CONFIG


class TestRAGSystemIntegration:
    """Integration test suite for RAG system"""

    def setup_method(self):
        """Set up test fixtures before each test method"""
        # Create temporary directory for test ChromaDB
        self.temp_dir = tempfile.mkdtemp()

        # Create test config with temp directory
        self.test_config = type(
            "Config",
            (),
            {
                "ANTHROPIC_API_KEY": "test-api-key",
                "ANTHROPIC_MODEL": "claude-3-sonnet-20241022",
                "EMBEDDING_MODEL": "all-MiniLM-L6-v2",
                "CHUNK_SIZE": 100,  # Small chunks for testing
                "CHUNK_OVERLAP": 20,
                "MAX_RESULTS": 3,
                "MAX_HISTORY": 2,
                "CHROMA_PATH": os.path.join(self.temp_dir, "test_chroma"),
            },
        )()

        # Create test document
        self.test_docs_dir = os.path.join(self.temp_dir, "docs")
        os.makedirs(self.test_docs_dir)

        with open(os.path.join(self.test_docs_dir, "test_course.txt"), "w") as f:
            f.write(
                """Course Title: Test Integration Course
Course Link: https://example.com/test-course
Course Instructor: Test Instructor

Lesson 1: Integration Testing Basics
Lesson Link: https://example.com/test-course/lesson1
Integration testing is a crucial phase in software testing where individual components are combined and tested as a group. The purpose is to expose faults in the interaction between integrated components.

Lesson 2: Advanced Integration Patterns
Lesson Link: https://example.com/test-course/lesson2
Advanced integration testing involves complex scenarios with multiple systems, APIs, and databases. Mocking and stubbing are essential techniques for isolating the system under test."""
            )

    def teardown_method(self):
        """Clean up after each test method"""
        shutil.rmtree(self.temp_dir)

    @patch("ai_generator.anthropic.Anthropic")
    def test_rag_system_initialization(self, mock_anthropic):
        """Test RAG system initializes all components correctly"""
        mock_anthropic.return_value = MagicMock()

        rag_system = RAGSystem(self.test_config)

        # Check all components are initialized
        assert rag_system.document_processor is not None
        assert rag_system.vector_store is not None
        assert rag_system.ai_generator is not None
        assert rag_system.session_manager is not None
        assert rag_system.tool_manager is not None

        # Check tools are registered
        tool_definitions = rag_system.tool_manager.get_tool_definitions()
        tool_names = [tool["name"] for tool in tool_definitions]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names

    @patch("ai_generator.anthropic.Anthropic")
    def test_add_course_document_success(self, mock_anthropic):
        """Test adding a single course document"""
        mock_anthropic.return_value = MagicMock()

        rag_system = RAGSystem(self.test_config)

        # Add test document
        test_file = os.path.join(self.test_docs_dir, "test_course.txt")
        course, chunk_count = rag_system.add_course_document(test_file)

        # Check course was processed
        assert course is not None
        assert course.title == "Test Integration Course"
        assert course.instructor == "Test Instructor"
        assert len(course.lessons) == 2
        assert chunk_count > 0

        # Check course was added to vector store
        existing_titles = rag_system.vector_store.get_existing_course_titles()
        assert "Test Integration Course" in existing_titles

    @patch("ai_generator.anthropic.Anthropic")
    def test_add_course_folder(self, mock_anthropic):
        """Test adding courses from a folder"""
        mock_anthropic.return_value = MagicMock()

        rag_system = RAGSystem(self.test_config)

        # Add all documents from folder
        total_courses, total_chunks = rag_system.add_course_folder(self.test_docs_dir)

        assert total_courses == 1
        assert total_chunks > 0

        # Verify course analytics
        analytics = rag_system.get_course_analytics()
        assert analytics["total_courses"] == 1
        assert "Test Integration Course" in analytics["course_titles"]

    @patch("ai_generator.anthropic.Anthropic")
    def test_add_nonexistent_file(self, mock_anthropic):
        """Test handling of nonexistent file"""
        mock_anthropic.return_value = MagicMock()

        rag_system = RAGSystem(self.test_config)

        course, chunk_count = rag_system.add_course_document("/nonexistent/file.txt")

        assert course is None
        assert chunk_count == 0

    @patch("ai_generator.anthropic.Anthropic")
    def test_query_without_tools_mock_response(self, mock_anthropic):
        """Test query processing with mocked AI response"""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MOCK_ANTHROPIC_RESPONSE_SIMPLE
        mock_anthropic.return_value = mock_client

        rag_system = RAGSystem(self.test_config)

        # Add test document first
        test_file = os.path.join(self.test_docs_dir, "test_course.txt")
        rag_system.add_course_document(test_file)

        # Query the system
        response, sources = rag_system.query("What is integration testing?")

        # Check response
        assert response == "This is a simple response without tools."
        assert isinstance(sources, list)

        # Verify AI generator was called with correct parameters
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args[1]
        assert "tools" in call_args
        assert "tool_choice" in call_args

    @patch("ai_generator.anthropic.Anthropic")
    def test_query_with_session_management(self, mock_anthropic):
        """Test query processing with session management"""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MOCK_ANTHROPIC_RESPONSE_SIMPLE
        mock_anthropic.return_value = mock_client

        rag_system = RAGSystem(self.test_config)

        # First query without session
        response1, sources1 = rag_system.query("First question")
        assert response1 == "This is a simple response without tools."

        # Second query with session from first
        session_id = "test_session"
        response2, sources2 = rag_system.query("Second question", session_id)

        # Check that conversation history is maintained
        # (We can't easily verify the exact content without more complex mocking)
        assert response2 == "This is a simple response without tools."

    @patch("ai_generator.anthropic.Anthropic")
    def test_query_tool_execution_flow(self, mock_anthropic):
        """Test that tool execution flow is properly set up"""
        mock_client = MagicMock()

        # Mock tool use response
        mock_tool_response = type(
            "MockResponse",
            (),
            {
                "content": [
                    type(
                        "Content",
                        (),
                        {
                            "type": "tool_use",
                            "name": "search_course_content",
                            "id": "tool_123",
                            "input": {
                                "query": "integration testing",
                                "course_name": None,
                                "lesson_number": None,
                            },
                        },
                    )()
                ],
                "stop_reason": "tool_use",
            },
        )()

        # Mock final response after tool execution
        mock_final_response = type(
            "MockResponse",
            (),
            {
                "content": [
                    type(
                        "Content",
                        (),
                        {
                            "text": "Integration testing is a crucial phase in software testing."
                        },
                    )()
                ],
                "stop_reason": "end_turn",
            },
        )()

        # Configure mock to return tool use first, then final response
        mock_client.messages.create.side_effect = [
            mock_tool_response,
            mock_final_response,
        ]
        mock_anthropic.return_value = mock_client

        rag_system = RAGSystem(self.test_config)

        # Add test document
        test_file = os.path.join(self.test_docs_dir, "test_course.txt")
        rag_system.add_course_document(test_file)

        # Query the system
        response, sources = rag_system.query("What is integration testing?")

        # Check that both API calls were made (initial + tool execution follow-up)
        assert mock_client.messages.create.call_count == 2

        # Check final response
        assert response == "Integration testing is a crucial phase in software testing."

    @patch("ai_generator.anthropic.Anthropic")
    def test_empty_vector_store_query(self, mock_anthropic):
        """Test query against empty vector store"""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MOCK_ANTHROPIC_RESPONSE_SIMPLE
        mock_anthropic.return_value = mock_client

        rag_system = RAGSystem(self.test_config)

        # Query without adding any documents
        response, sources = rag_system.query("What is integration testing?")

        # Should still work but likely return generic response
        assert response == "This is a simple response without tools."
        assert isinstance(sources, list)

    @patch("ai_generator.anthropic.Anthropic")
    def test_course_analytics_empty(self, mock_anthropic):
        """Test course analytics with empty vector store"""
        mock_anthropic.return_value = MagicMock()

        rag_system = RAGSystem(self.test_config)

        analytics = rag_system.get_course_analytics()

        assert analytics["total_courses"] == 0
        assert analytics["course_titles"] == []

    @patch("ai_generator.anthropic.Anthropic")
    def test_duplicate_course_handling(self, mock_anthropic):
        """Test that duplicate courses are not added twice"""
        mock_anthropic.return_value = MagicMock()

        rag_system = RAGSystem(self.test_config)

        test_file = os.path.join(self.test_docs_dir, "test_course.txt")

        # Add the same document twice
        course1, chunks1 = rag_system.add_course_document(test_file)
        course2, chunks2 = rag_system.add_course_document(test_file)

        # First add should succeed
        assert course1 is not None
        assert chunks1 > 0

        # Second add should also succeed (current implementation doesn't prevent duplicates in single file adds)
        assert course2 is not None
        assert chunks2 > 0

        # However, folder-based adding should skip duplicates
        total_courses, total_chunks = rag_system.add_course_folder(self.test_docs_dir)

        # Should skip the already existing course
        assert total_courses == 0  # No new courses added
        assert total_chunks == 0

    @patch("ai_generator.anthropic.Anthropic")
    def test_clear_existing_data(self, mock_anthropic):
        """Test clearing existing data in folder add"""
        mock_anthropic.return_value = MagicMock()

        rag_system = RAGSystem(self.test_config)

        # Add initial data
        test_file = os.path.join(self.test_docs_dir, "test_course.txt")
        rag_system.add_course_document(test_file)

        # Verify data exists
        analytics_before = rag_system.get_course_analytics()
        assert analytics_before["total_courses"] == 1

        # Add folder with clear_existing=True
        total_courses, total_chunks = rag_system.add_course_folder(
            self.test_docs_dir, clear_existing=True
        )

        # Should still have the same course (re-added after clearing)
        analytics_after = rag_system.get_course_analytics()
        assert analytics_after["total_courses"] == 1
        assert total_courses == 1  # One course was added
        assert total_chunks > 0

    def test_config_validation(self):
        """Test that configuration is properly used"""
        # Test with invalid config (missing API key)
        bad_config = type(
            "Config",
            (),
            {
                "ANTHROPIC_API_KEY": "",  # Empty API key
                "ANTHROPIC_MODEL": "claude-3-sonnet-20241022",
                "EMBEDDING_MODEL": "all-MiniLM-L6-v2",
                "CHUNK_SIZE": 100,
                "CHUNK_OVERLAP": 20,
                "MAX_RESULTS": 3,
                "MAX_HISTORY": 2,
                "CHROMA_PATH": os.path.join(self.temp_dir, "test_chroma"),
            },
        )()

        # RAG system should initialize even with empty API key
        # (The Anthropic client will be created but API calls will fail)
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value = MagicMock()
            rag_system = RAGSystem(bad_config)
            assert rag_system.ai_generator is not None


if __name__ == "__main__":
    pytest.main([__file__])
