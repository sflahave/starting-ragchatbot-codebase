"""
Mock data and fixtures for testing the RAG system components
"""
from typing import List, Dict, Any
from models import Course, Lesson, CourseChunk
from vector_store import SearchResults


# Test Courses
MOCK_LESSON_1 = Lesson(
    lesson_number=1,
    title="Introduction to AI", 
    lesson_link="https://example.com/course1/lesson1"
)

MOCK_LESSON_2 = Lesson(
    lesson_number=2,
    title="Machine Learning Basics",
    lesson_link="https://example.com/course1/lesson2"
)

MOCK_COURSE_1 = Course(
    title="Introduction to Artificial Intelligence",
    course_link="https://example.com/course1",
    instructor="Dr. Jane Smith",
    lessons=[MOCK_LESSON_1, MOCK_LESSON_2]
)

MOCK_LESSON_3 = Lesson(
    lesson_number=1,
    title="Python Fundamentals",
    lesson_link="https://example.com/course2/lesson1"
)

MOCK_COURSE_2 = Course(
    title="Python Programming",
    course_link="https://example.com/course2", 
    instructor="John Doe",
    lessons=[MOCK_LESSON_3]
)

MOCK_COURSES = [MOCK_COURSE_1, MOCK_COURSE_2]

# Test Course Chunks
MOCK_CHUNKS = [
    CourseChunk(
        content="Artificial Intelligence is the simulation of human intelligence in machines that are programmed to think and learn like humans.",
        course_title="Introduction to Artificial Intelligence",
        lesson_number=1,
        chunk_index=0
    ),
    CourseChunk(
        content="Machine learning is a subset of AI that enables machines to automatically learn and improve from experience without being explicitly programmed.",
        course_title="Introduction to Artificial Intelligence", 
        lesson_number=2,
        chunk_index=1
    ),
    CourseChunk(
        content="Python is a high-level, interpreted programming language with dynamic semantics. Its built-in data structures make it attractive for rapid application development.",
        course_title="Python Programming",
        lesson_number=1,
        chunk_index=0
    )
]

# Mock Search Results
MOCK_SEARCH_RESULTS_SUCCESS = SearchResults(
    documents=[
        "Artificial Intelligence is the simulation of human intelligence in machines that are programmed to think and learn like humans.",
        "Machine learning is a subset of AI that enables machines to automatically learn and improve from experience without being explicitly programmed."
    ],
    metadata=[
        {"course_title": "Introduction to Artificial Intelligence", "lesson_number": 1},
        {"course_title": "Introduction to Artificial Intelligence", "lesson_number": 2}
    ],
    distances=[0.1, 0.2]
)

MOCK_SEARCH_RESULTS_EMPTY = SearchResults(
    documents=[],
    metadata=[],
    distances=[]
)

MOCK_SEARCH_RESULTS_ERROR = SearchResults(
    documents=[],
    metadata=[],
    distances=[],
    error="Database connection failed"
)

# Mock ChromaDB Results
MOCK_CHROMA_RESULTS_SUCCESS = {
    'documents': [["AI is the simulation of human intelligence", "Machine learning is a subset of AI"]],
    'metadatas': [[
        {"course_title": "Introduction to Artificial Intelligence", "lesson_number": 1},
        {"course_title": "Introduction to Artificial Intelligence", "lesson_number": 2}
    ]],
    'distances': [[0.1, 0.2]]
}

MOCK_CHROMA_RESULTS_EMPTY = {
    'documents': [[]],
    'metadatas': [[]],
    'distances': [[]]
}

# Mock Anthropic API Responses
MOCK_ANTHROPIC_RESPONSE_SIMPLE = type('MockResponse', (), {
    'content': [type('Content', (), {'text': 'This is a simple response without tools.'})()],
    'stop_reason': 'end_turn'
})()

MOCK_ANTHROPIC_RESPONSE_TOOL_USE = type('MockResponse', (), {
    'content': [
        type('Content', (), {
            'type': 'tool_use',
            'name': 'search_course_content',
            'id': 'tool_use_123',
            'input': {'query': 'artificial intelligence', 'course_name': None, 'lesson_number': None}
        })()
    ],
    'stop_reason': 'tool_use'
})()

MOCK_ANTHROPIC_RESPONSE_FINAL = type('MockResponse', (), {
    'content': [type('Content', (), {'text': 'Based on the search results, AI is the simulation of human intelligence in machines.'})()],
    'stop_reason': 'end_turn'
})()

# Sequential Tool Calling Mock Responses
MOCK_SEQUENTIAL_ROUND_1_TOOL_USE = type('MockResponse', (), {
    'content': [
        type('Content', (), {
            'type': 'tool_use',
            'name': 'get_course_outline',
            'id': 'tool_use_outline_123',
            'input': {'course_title': 'Introduction to Artificial Intelligence'}
        })()
    ],
    'stop_reason': 'tool_use'
})()

MOCK_SEQUENTIAL_ROUND_2_TOOL_USE = type('MockResponse', (), {
    'content': [
        type('Content', (), {
            'type': 'tool_use',
            'name': 'search_course_content',
            'id': 'tool_use_search_456',
            'input': {'query': 'machine learning basics', 'course_name': None, 'lesson_number': None}
        })()
    ],
    'stop_reason': 'tool_use'
})()

MOCK_SEQUENTIAL_FINAL_RESPONSE = type('MockResponse', (), {
    'content': [type('Content', (), {'text': 'Based on the course outline and search results, lesson 2 covers machine learning basics which is fundamental to AI.'})()],
    'stop_reason': 'end_turn'
})()

MOCK_SEQUENTIAL_NO_TOOLS_RESPONSE = type('MockResponse', (), {
    'content': [type('Content', (), {'text': 'I can answer that directly without needing to search: AI is a broad field of computer science.'})()],
    'stop_reason': 'end_turn'
})()

# Multiple tool use in single response
MOCK_MULTIPLE_TOOLS_RESPONSE = type('MockResponse', (), {
    'content': [
        type('Content', (), {
            'type': 'tool_use',
            'name': 'search_course_content',
            'id': 'tool_1',
            'input': {'query': 'AI basics', 'course_name': None, 'lesson_number': None}
        })(),
        type('Content', (), {
            'type': 'tool_use',
            'name': 'get_course_outline',
            'id': 'tool_2',
            'input': {'course_title': 'AI Course'}
        })()
    ],
    'stop_reason': 'tool_use'
})()

# Tool execution results for testing
MOCK_COURSE_OUTLINE_RESULT = """
Course: Introduction to Artificial Intelligence
Instructor: Dr. Jane Smith
Link: https://example.com/course1

Lessons:
1. Introduction to AI
2. Machine Learning Basics
"""

MOCK_SEARCH_CONTENT_RESULT = """
Found 2 relevant sections:
1. Machine learning is a subset of AI that enables machines to learn from data
2. Supervised learning uses labeled data to train models
"""

# Test Configuration
MOCK_CONFIG = type('Config', (), {
    'ANTHROPIC_API_KEY': 'test-api-key',
    'ANTHROPIC_MODEL': 'claude-3-sonnet-20241022',
    'EMBEDDING_MODEL': 'all-MiniLM-L6-v2', 
    'CHUNK_SIZE': 800,
    'CHUNK_OVERLAP': 100,
    'MAX_RESULTS': 5,  # Fixed the 0 value issue
    'MAX_HISTORY': 2,
    'CHROMA_PATH': './test_chroma_db'
})()

# Mock Functions
def create_mock_vector_store():
    """Create a mock vector store with controlled behavior"""
    from unittest.mock import MagicMock
    
    mock_store = MagicMock()
    
    # Default successful search
    mock_store.search.return_value = MOCK_SEARCH_RESULTS_SUCCESS
    mock_store._resolve_course_name.return_value = "Introduction to Artificial Intelligence"
    mock_store.get_all_courses_metadata.return_value = [
        {
            'title': 'Introduction to Artificial Intelligence',
            'instructor': 'Dr. Jane Smith',
            'course_link': 'https://example.com/course1',
            'lessons': [
                {'lesson_number': 1, 'lesson_title': 'Introduction to AI', 'lesson_link': 'https://example.com/course1/lesson1'},
                {'lesson_number': 2, 'lesson_title': 'Machine Learning Basics', 'lesson_link': 'https://example.com/course1/lesson2'}
            ]
        }
    ]
    mock_store.get_lesson_link.return_value = "https://example.com/course1/lesson1"
    
    return mock_store

def create_mock_anthropic_client():
    """Create a mock Anthropic client with controlled responses"""
    from unittest.mock import MagicMock
    
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MOCK_ANTHROPIC_RESPONSE_SIMPLE
    
    return mock_client

def create_sequential_mock_responses():
    """Create a list of mock responses for sequential tool calling tests"""
    return [
        MOCK_SEQUENTIAL_ROUND_1_TOOL_USE,
        MOCK_SEQUENTIAL_ROUND_2_TOOL_USE, 
        MOCK_SEQUENTIAL_FINAL_RESPONSE
    ]

def create_mock_tool_manager():
    """Create a mock tool manager with controlled tool execution results"""
    from unittest.mock import MagicMock
    
    mock_manager = MagicMock()
    mock_manager.execute_tool.side_effect = [
        MOCK_COURSE_OUTLINE_RESULT,
        MOCK_SEARCH_CONTENT_RESULT
    ]
    
    return mock_manager