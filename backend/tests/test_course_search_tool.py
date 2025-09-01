"""
Unit tests for CourseSearchTool functionality
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from search_tools import CourseSearchTool
from tests.fixtures.mock_data import (
    MOCK_SEARCH_RESULTS_EMPTY,
    MOCK_SEARCH_RESULTS_ERROR,
    MOCK_SEARCH_RESULTS_SUCCESS,
    create_mock_vector_store,
)
from vector_store import SearchResults


class TestCourseSearchTool:
    """Test suite for CourseSearchTool"""

    def setup_method(self):
        """Set up test fixtures before each test method"""
        self.mock_vector_store = create_mock_vector_store()
        self.search_tool = CourseSearchTool(self.mock_vector_store)

    def test_tool_definition(self):
        """Test that tool definition is properly structured"""
        definition = self.search_tool.get_tool_definition()

        # Check basic structure
        assert "name" in definition
        assert "description" in definition
        assert "input_schema" in definition

        # Check specific values
        assert definition["name"] == "search_course_content"
        assert "properties" in definition["input_schema"]
        assert "required" in definition["input_schema"]

        # Check required fields
        assert "query" in definition["input_schema"]["required"]

        # Check optional fields exist
        properties = definition["input_schema"]["properties"]
        assert "query" in properties
        assert "course_name" in properties
        assert "lesson_number" in properties

    def test_execute_successful_search(self):
        """Test successful search with results"""
        # Configure mock to return successful results
        self.mock_vector_store.search.return_value = MOCK_SEARCH_RESULTS_SUCCESS

        result = self.search_tool.execute(query="artificial intelligence")

        # Verify search was called correctly
        self.mock_vector_store.search.assert_called_once_with(
            query="artificial intelligence", course_name=None, lesson_number=None
        )

        # Check result formatting
        assert "[Introduction to Artificial Intelligence - Lesson 1]" in result
        assert "[Introduction to Artificial Intelligence - Lesson 2]" in result
        assert "Artificial Intelligence is the simulation" in result
        assert "Machine learning is a subset of AI" in result

        # Check sources were tracked
        assert len(self.search_tool.last_sources) == 2
        assert (
            self.search_tool.last_sources[0]["text"]
            == "Introduction to Artificial Intelligence - Lesson 1"
        )
        assert (
            self.search_tool.last_sources[1]["text"]
            == "Introduction to Artificial Intelligence - Lesson 2"
        )

    def test_execute_with_course_name_filter(self):
        """Test search with course name filter"""
        self.mock_vector_store.search.return_value = MOCK_SEARCH_RESULTS_SUCCESS

        result = self.search_tool.execute(
            query="artificial intelligence", course_name="Introduction to AI"
        )

        # Verify search was called with course filter
        self.mock_vector_store.search.assert_called_once_with(
            query="artificial intelligence",
            course_name="Introduction to AI",
            lesson_number=None,
        )

        assert "Introduction to Artificial Intelligence" in result

    def test_execute_with_lesson_number_filter(self):
        """Test search with lesson number filter"""
        self.mock_vector_store.search.return_value = MOCK_SEARCH_RESULTS_SUCCESS

        result = self.search_tool.execute(
            query="artificial intelligence", lesson_number=1
        )

        # Verify search was called with lesson filter
        self.mock_vector_store.search.assert_called_once_with(
            query="artificial intelligence", course_name=None, lesson_number=1
        )

        assert "Introduction to Artificial Intelligence" in result

    def test_execute_with_both_filters(self):
        """Test search with both course name and lesson number filters"""
        self.mock_vector_store.search.return_value = MOCK_SEARCH_RESULTS_SUCCESS

        result = self.search_tool.execute(
            query="artificial intelligence",
            course_name="Introduction to AI",
            lesson_number=2,
        )

        # Verify search was called with both filters
        self.mock_vector_store.search.assert_called_once_with(
            query="artificial intelligence",
            course_name="Introduction to AI",
            lesson_number=2,
        )

        assert "Introduction to Artificial Intelligence" in result

    def test_execute_empty_results(self):
        """Test handling of empty search results"""
        self.mock_vector_store.search.return_value = MOCK_SEARCH_RESULTS_EMPTY

        result = self.search_tool.execute(query="nonexistent topic")

        # Should return empty results message
        assert "No relevant content found" in result
        assert self.search_tool.last_sources == []

    def test_execute_empty_results_with_filters(self):
        """Test empty results message includes filter information"""
        self.mock_vector_store.search.return_value = MOCK_SEARCH_RESULTS_EMPTY

        result = self.search_tool.execute(
            query="nonexistent topic",
            course_name="Nonexistent Course",
            lesson_number=99,
        )

        # Should include filter info in message
        assert (
            "No relevant content found in course 'Nonexistent Course' in lesson 99"
            in result
        )

    def test_execute_search_error(self):
        """Test handling of search errors"""
        self.mock_vector_store.search.return_value = MOCK_SEARCH_RESULTS_ERROR

        result = self.search_tool.execute(query="any query")

        # Should return the error message
        assert result == "Database connection failed"
        assert self.search_tool.last_sources == []

    def test_execute_vector_store_exception(self):
        """Test handling of vector store exceptions"""
        self.mock_vector_store.search.side_effect = Exception("Vector store crashed")

        # This should raise the exception since there's no try/catch in execute()
        with pytest.raises(Exception, match="Vector store crashed"):
            self.search_tool.execute(query="any query")

    def test_format_results_with_lesson_links(self):
        """Test that lesson links are properly retrieved and stored"""
        # Setup mock to return lesson links
        self.mock_vector_store.get_lesson_link.return_value = (
            "https://example.com/lesson1"
        )

        # Create search results with lesson numbers
        search_results = SearchResults(
            documents=["Test content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 1}],
            distances=[0.1],
        )
        self.mock_vector_store.search.return_value = search_results

        result = self.search_tool.execute(query="test")

        # Check that get_lesson_link was called
        self.mock_vector_store.get_lesson_link.assert_called_once_with("Test Course", 1)

        # Check that source has URL
        assert len(self.search_tool.last_sources) == 1
        assert self.search_tool.last_sources[0]["url"] == "https://example.com/lesson1"

    def test_format_results_without_lesson_number(self):
        """Test formatting when lesson number is None"""
        search_results = SearchResults(
            documents=["Test content"],
            metadata=[{"course_title": "Test Course", "lesson_number": None}],
            distances=[0.1],
        )
        self.mock_vector_store.search.return_value = search_results

        result = self.search_tool.execute(query="test")

        # Should not call get_lesson_link when lesson_number is None
        self.mock_vector_store.get_lesson_link.assert_not_called()

        # Header should not include lesson number
        assert "[Test Course]" in result
        assert (
            "Lesson" not in result.split("\n")[0]
        )  # Check first line doesn't have "Lesson"

        # Source should not have URL
        assert len(self.search_tool.last_sources) == 1
        assert self.search_tool.last_sources[0]["url"] is None

    def test_sources_reset_between_searches(self):
        """Test that sources are properly tracked and reset"""
        self.mock_vector_store.search.return_value = MOCK_SEARCH_RESULTS_SUCCESS

        # First search
        self.search_tool.execute(query="first query")
        first_sources = self.search_tool.last_sources.copy()

        # Second search with different results
        single_result = SearchResults(
            documents=["Single result"],
            metadata=[{"course_title": "Single Course", "lesson_number": 1}],
            distances=[0.1],
        )
        self.mock_vector_store.search.return_value = single_result

        self.search_tool.execute(query="second query")

        # Sources should be different
        assert len(first_sources) == 2
        assert len(self.search_tool.last_sources) == 1
        assert self.search_tool.last_sources[0]["text"] == "Single Course - Lesson 1"


if __name__ == "__main__":
    pytest.main([__file__])
