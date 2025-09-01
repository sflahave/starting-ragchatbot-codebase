"""
Unit tests for AIGenerator functionality
"""
import pytest
import sys
import os
from unittest.mock import MagicMock, patch, Mock

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_generator import AIGenerator, ConversationState
from tests.fixtures.mock_data import (
    MOCK_ANTHROPIC_RESPONSE_SIMPLE,
    MOCK_ANTHROPIC_RESPONSE_TOOL_USE,
    MOCK_ANTHROPIC_RESPONSE_FINAL,
    MOCK_SEQUENTIAL_ROUND_1_TOOL_USE,
    MOCK_SEQUENTIAL_ROUND_2_TOOL_USE,
    MOCK_SEQUENTIAL_FINAL_RESPONSE,
    MOCK_SEQUENTIAL_NO_TOOLS_RESPONSE,
    MOCK_MULTIPLE_TOOLS_RESPONSE,
    MOCK_COURSE_OUTLINE_RESULT,
    MOCK_SEARCH_CONTENT_RESULT,
    MOCK_CONFIG,
    create_mock_anthropic_client,
    create_sequential_mock_responses,
    create_mock_tool_manager
)


class TestAIGenerator:
    """Test suite for AIGenerator"""
    
    def setup_method(self):
        """Set up test fixtures before each test method"""
        # Create AIGenerator with test config
        self.ai_generator = AIGenerator(
            api_key="test-api-key",
            model="claude-3-sonnet-20241022"
        )
        
        # Mock the Anthropic client
        self.mock_client = create_mock_anthropic_client()
        self.ai_generator.client = self.mock_client
    
    def test_initialization(self):
        """Test AIGenerator initialization"""
        assert self.ai_generator.model == "claude-3-sonnet-20241022"
        assert "model" in self.ai_generator.base_params
        assert "temperature" in self.ai_generator.base_params
        assert "max_tokens" in self.ai_generator.base_params
        
        # Check default values
        assert self.ai_generator.base_params["temperature"] == 0
        assert self.ai_generator.base_params["max_tokens"] == 800
    
    def test_system_prompt_content(self):
        """Test that system prompt contains expected content"""
        system_prompt = self.ai_generator.SYSTEM_PROMPT
        
        # Check key elements are present
        assert "course materials" in system_prompt.lower()
        assert "search_course_content" in system_prompt or "Course Content Search" in system_prompt
        assert "get_course_outline" in system_prompt or "Course Outline" in system_prompt
        assert "tools" in system_prompt.lower()
    
    def test_generate_response_without_tools(self):
        """Test basic response generation without tools"""
        self.mock_client.messages.create.return_value = MOCK_ANTHROPIC_RESPONSE_SIMPLE
        
        response = self.ai_generator.generate_response("What is artificial intelligence?")
        
        # Check that API was called correctly
        self.mock_client.messages.create.assert_called_once()
        call_args = self.mock_client.messages.create.call_args[1]
        
        assert call_args["model"] == "claude-3-sonnet-20241022"
        assert call_args["temperature"] == 0
        assert call_args["max_tokens"] == 800
        assert len(call_args["messages"]) == 1
        assert call_args["messages"][0]["role"] == "user"
        assert call_args["messages"][0]["content"] == "What is artificial intelligence?"
        assert "tools" not in call_args
        
        # Check response
        assert response == "This is a simple response without tools."
    
    def test_generate_response_with_conversation_history(self):
        """Test response generation with conversation history"""
        self.mock_client.messages.create.return_value = MOCK_ANTHROPIC_RESPONSE_SIMPLE
        
        history = "Previous conversation context"
        response = self.ai_generator.generate_response(
            "What is AI?",
            conversation_history=history
        )
        
        # Check that system prompt includes history
        call_args = self.mock_client.messages.create.call_args[1]
        assert history in call_args["system"]
        
        assert response == "This is a simple response without tools."
    
    def test_generate_response_with_tools_no_tool_use(self):
        """Test response generation with tools available but not used"""
        self.mock_client.messages.create.return_value = MOCK_ANTHROPIC_RESPONSE_SIMPLE
        
        mock_tools = [{"name": "search_course_content", "description": "Search courses"}]
        
        response = self.ai_generator.generate_response(
            "Hello",
            tools=mock_tools
        )
        
        # Check that tools were provided to API
        call_args = self.mock_client.messages.create.call_args[1]
        assert "tools" in call_args
        assert call_args["tools"] == mock_tools
        assert call_args["tool_choice"] == {"type": "auto"}
        
        assert response == "This is a simple response without tools."
    
    def test_generate_response_with_tool_use(self):
        """Test response generation when tools are used (now uses sequential calling)"""
        # Mock sequential responses - tool use then completion
        self.mock_client.messages.create.side_effect = [
            MOCK_ANTHROPIC_RESPONSE_TOOL_USE,
            MOCK_ANTHROPIC_RESPONSE_FINAL
        ]
        
        mock_tools = [{"name": "search_course_content", "description": "Search courses"}]
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "Search results found"
        
        response = self.ai_generator.generate_response(
            "Search for AI content",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        # Check that tool was executed
        mock_tool_manager.execute_tool.assert_called_once()
        
        # Should make 2 API calls (tool use + completion)
        assert self.mock_client.messages.create.call_count == 2
        
        assert response == "Based on the search results, AI is the simulation of human intelligence in machines."
    
    def test_handle_tool_execution(self):
        """Test tool execution handling"""
        # Create mock tool manager
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "Search results found"
        
        # Mock the final API call
        self.mock_client.messages.create.return_value = MOCK_ANTHROPIC_RESPONSE_FINAL
        
        # Base parameters for the API call
        base_params = {
            "model": "claude-3-sonnet-20241022",
            "temperature": 0,
            "max_tokens": 800,
            "messages": [{"role": "user", "content": "Search for AI"}],
            "system": self.ai_generator.SYSTEM_PROMPT
        }
        
        response = self.ai_generator._handle_tool_execution(
            MOCK_ANTHROPIC_RESPONSE_TOOL_USE,
            base_params,
            mock_tool_manager
        )
        
        # Check tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            'search_course_content',
            query='artificial intelligence',
            course_name=None,
            lesson_number=None
        )
        
        # Check final API call was made
        assert self.mock_client.messages.create.call_count == 1
        final_call_args = self.mock_client.messages.create.call_args[1]
        
        # Should have 3 messages: original user message, assistant tool use, user tool results
        assert len(final_call_args["messages"]) == 3
        assert final_call_args["messages"][0]["role"] == "user"
        assert final_call_args["messages"][1]["role"] == "assistant"
        assert final_call_args["messages"][2]["role"] == "user"
        
        # Check tool results message
        tool_results_message = final_call_args["messages"][2]
        assert "tool_result" in str(tool_results_message["content"])
        assert "Search results found" in str(tool_results_message["content"])
        
        assert response == "Based on the search results, AI is the simulation of human intelligence in machines."
    
    def test_handle_tool_execution_multiple_tools(self):
        """Test handling multiple tool calls in one response"""
        # Create mock response with multiple tool uses
        mock_response = type('MockResponse', (), {
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
        
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = ["Search results", "Course outline"]
        
        self.mock_client.messages.create.return_value = MOCK_ANTHROPIC_RESPONSE_FINAL
        
        base_params = {
            "model": "claude-3-sonnet-20241022",
            "messages": [{"role": "user", "content": "Tell me about AI"}],
            "system": self.ai_generator.SYSTEM_PROMPT
        }
        
        response = self.ai_generator._handle_tool_execution(
            mock_response,
            base_params,
            mock_tool_manager
        )
        
        # Check both tools were executed
        assert mock_tool_manager.execute_tool.call_count == 2
        
        # Check the calls were made with correct parameters
        calls = mock_tool_manager.execute_tool.call_args_list
        assert calls[0][0] == ('search_course_content',)
        assert calls[1][0] == ('get_course_outline',)
        
        assert response == "Based on the search results, AI is the simulation of human intelligence in machines."
    
    def test_handle_tool_execution_tool_manager_error(self):
        """Test handling of tool manager errors"""
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = Exception("Tool execution failed")
        
        base_params = {
            "model": "claude-3-sonnet-20241022",
            "messages": [{"role": "user", "content": "Search"}],
            "system": self.ai_generator.SYSTEM_PROMPT
        }
        
        # This should raise the exception since there's no error handling
        with pytest.raises(Exception, match="Tool execution failed"):
            self.ai_generator._handle_tool_execution(
                MOCK_ANTHROPIC_RESPONSE_TOOL_USE,
                base_params,
                mock_tool_manager
            )
    
    def test_api_call_parameters_structure(self):
        """Test that API call parameters are structured correctly"""
        self.mock_client.messages.create.return_value = MOCK_ANTHROPIC_RESPONSE_SIMPLE
        
        # Test with all optional parameters
        mock_tools = [{"name": "test_tool"}]
        mock_tool_manager = MagicMock()
        
        self.ai_generator.generate_response(
            query="Test query",
            conversation_history="Previous context",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        call_args = self.mock_client.messages.create.call_args[1]
        
        # Check all expected parameters are present
        expected_params = ["model", "temperature", "max_tokens", "messages", "system", "tools", "tool_choice"]
        for param in expected_params:
            assert param in call_args
        
        # Check parameter values
        assert call_args["model"] == "claude-3-sonnet-20241022"
        assert call_args["temperature"] == 0
        assert call_args["max_tokens"] == 800
        assert call_args["tools"] == mock_tools
        assert call_args["tool_choice"] == {"type": "auto"}
        assert "Previous context" in call_args["system"]
    
    def test_anthropic_api_error_handling(self):
        """Test handling of Anthropic API errors"""
        # Mock API to raise an exception
        self.mock_client.messages.create.side_effect = Exception("API request failed")
        
        with pytest.raises(Exception, match="API request failed"):
            self.ai_generator.generate_response("Test query")


class TestSequentialToolCalling:
    """Test suite for sequential tool calling functionality"""
    
    def setup_method(self):
        """Set up test fixtures for sequential tool calling tests"""
        self.ai_generator = AIGenerator(
            api_key="test-api-key",
            model="claude-3-sonnet-20241022"
        )
        self.mock_client = create_mock_anthropic_client()
        self.ai_generator.client = self.mock_client
    
    def test_two_rounds_sequential_tool_use_natural_completion(self):
        """Test two rounds of tool calling with natural completion"""
        # Set up sequential responses - second round ends naturally
        self.mock_client.messages.create.side_effect = [
            MOCK_SEQUENTIAL_ROUND_1_TOOL_USE,
            MOCK_SEQUENTIAL_FINAL_RESPONSE  # Second round completes naturally
        ]
        
        # Set up tool manager
        mock_tool_manager = create_mock_tool_manager()
        mock_tools = [
            {"name": "get_course_outline", "description": "Get course outline"},
            {"name": "search_course_content", "description": "Search course content"}
        ]
        
        response = self.ai_generator.generate_response(
            "What does lesson 2 of the AI course cover?",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        # Verify API calls made - should be 2 (first tool use + natural completion)
        assert self.mock_client.messages.create.call_count == 2
        
        # Verify first API call - initial query
        first_call = self.mock_client.messages.create.call_args_list[0][1]
        assert len(first_call["messages"]) == 1
        assert first_call["messages"][0]["role"] == "user"
        assert "tools" in first_call
        
        # Verify second API call - after first tool execution
        second_call = self.mock_client.messages.create.call_args_list[1][1]
        assert len(second_call["messages"]) == 3  # user + assistant + tool_results
        assert second_call["messages"][1]["role"] == "assistant"
        assert second_call["messages"][2]["role"] == "user"
        assert "tools" in second_call
        
        # Verify tool execution - should be called once
        assert mock_tool_manager.execute_tool.call_count == 1
        tool_calls = mock_tool_manager.execute_tool.call_args_list
        assert tool_calls[0][0] == ('get_course_outline',)
        
        # Verify final response
        assert "lesson 2 covers machine learning basics" in response
    
    def test_single_round_with_tools_natural_termination(self):
        """Test single round termination when Claude doesn't need more tools"""
        self.mock_client.messages.create.side_effect = [
            MOCK_ANTHROPIC_RESPONSE_TOOL_USE,
            MOCK_SEQUENTIAL_FINAL_RESPONSE
        ]
        
        mock_tool_manager = create_mock_tool_manager()
        mock_tools = [{"name": "search_course_content", "description": "Search content"}]
        
        response = self.ai_generator.generate_response(
            "What is AI?",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        # Should make 2 API calls: tool use + final response
        assert self.mock_client.messages.create.call_count == 2
        
        # Verify tool was executed once
        assert mock_tool_manager.execute_tool.call_count == 1
        
        # Verify response
        assert "lesson 2 covers machine learning basics" in response
    
    def test_no_tools_first_response_termination(self):
        """Test termination when first response doesn't use tools"""
        self.mock_client.messages.create.return_value = MOCK_SEQUENTIAL_NO_TOOLS_RESPONSE
        
        mock_tool_manager = create_mock_tool_manager()
        mock_tools = [{"name": "search_course_content", "description": "Search content"}]
        
        response = self.ai_generator.generate_response(
            "What is AI in general?",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        # Should make only 1 API call
        assert self.mock_client.messages.create.call_count == 1
        
        # Should not execute any tools
        assert mock_tool_manager.execute_tool.call_count == 0
        
        # Verify direct response
        assert "I can answer that directly" in response
    
    def test_two_full_rounds_with_tools(self):
        """Test two complete rounds of tool execution"""
        # Set up responses for two complete tool rounds
        self.mock_client.messages.create.side_effect = [
            MOCK_SEQUENTIAL_ROUND_1_TOOL_USE,  # Round 1: wants tools
            MOCK_SEQUENTIAL_ROUND_2_TOOL_USE,  # Round 2: still wants tools  
            MOCK_SEQUENTIAL_FINAL_RESPONSE      # Round 3: natural completion
        ]
        
        mock_tool_manager = create_mock_tool_manager()
        mock_tools = [{"name": "search_course_content", "description": "Search content"}]
        
        # Need to modify the implementation to allow 3 rounds for this test
        original_max = self.ai_generator.MAX_ROUNDS
        self.ai_generator.MAX_ROUNDS = 3  # Allow 3 rounds for this test
        
        try:
            response = self.ai_generator.generate_response(
                "Complex query requiring multiple searches",
                tools=mock_tools,
                tool_manager=mock_tool_manager
            )
            
            # Should make exactly 3 API calls
            assert self.mock_client.messages.create.call_count == 3
            
            # Should execute tools twice (rounds 1 and 2)
            assert mock_tool_manager.execute_tool.call_count == 2
            
            # All calls should have tools available
            for i in range(3):
                call = self.mock_client.messages.create.call_args_list[i][1]
                assert "tools" in call
            
            assert "lesson 2 covers machine learning basics" in response
            
        finally:
            # Restore original max rounds
            self.ai_generator.MAX_ROUNDS = original_max
    
    def test_max_rounds_reached_forced_completion(self):
        """Test forced completion when max rounds (2) is reached"""
        # Set up responses where Claude wants tools beyond max rounds
        self.mock_client.messages.create.side_effect = [
            MOCK_SEQUENTIAL_ROUND_1_TOOL_USE,   # Round 1: wants tools
            MOCK_SEQUENTIAL_ROUND_2_TOOL_USE,   # Round 2: still wants tools (hits limit)
            MOCK_SEQUENTIAL_FINAL_RESPONSE      # Forced final response
        ]
        
        mock_tool_manager = create_mock_tool_manager()
        mock_tools = [{"name": "search_course_content", "description": "Search content"}]
        
        response = self.ai_generator.generate_response(
            "Complex query requiring multiple searches",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        # Should make exactly 3 API calls (round 1 + round 2 hit limit + forced final)
        assert self.mock_client.messages.create.call_count == 3
        
        # Should execute tools only once (round 1 only, round 2 hits max limit)
        assert mock_tool_manager.execute_tool.call_count == 1
        
        # First two calls should have tools
        first_call = self.mock_client.messages.create.call_args_list[0][1]
        second_call = self.mock_client.messages.create.call_args_list[1][1]
        assert "tools" in first_call
        assert "tools" in second_call
        
        # Final API call should NOT include tools (forced completion)
        final_call = self.mock_client.messages.create.call_args_list[2][1]
        assert "tools" not in final_call
        
        assert "lesson 2 covers machine learning basics" in response
    
    def test_conversation_context_preservation(self):
        """Test that conversation context is preserved across rounds"""
        self.mock_client.messages.create.side_effect = [
            MOCK_SEQUENTIAL_ROUND_1_TOOL_USE,
            MOCK_SEQUENTIAL_FINAL_RESPONSE
        ]
        
        mock_tool_manager = create_mock_tool_manager()
        mock_tools = [{"name": "get_course_outline", "description": "Get outline"}]
        
        response = self.ai_generator.generate_response(
            "What's in the AI course?",
            conversation_history="User previously asked about machine learning",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        # Verify conversation history is included in all API calls
        for call_args in self.mock_client.messages.create.call_args_list:
            system_prompt = call_args[1]["system"]
            assert "User previously asked about machine learning" in system_prompt
    
    def test_tool_execution_error_handling(self):
        """Test graceful handling of tool execution errors"""
        self.mock_client.messages.create.return_value = MOCK_SEQUENTIAL_ROUND_1_TOOL_USE
        
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = Exception("Tool failed")
        mock_tools = [{"name": "search_course_content", "description": "Search content"}]
        
        response = self.ai_generator.generate_response(
            "Search for something",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        # Should handle error gracefully
        assert "error while using the search tools" in response
        assert mock_tool_manager.execute_tool.call_count == 1
    
    def test_api_error_handling(self):
        """Test graceful handling of API errors during conversation loop"""
        self.mock_client.messages.create.side_effect = Exception("API failed")
        
        mock_tool_manager = create_mock_tool_manager()
        mock_tools = [{"name": "search_course_content", "description": "Search content"}]
        
        response = self.ai_generator.generate_response(
            "Search for something",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        # Should handle error gracefully
        assert "error while processing your request" in response
    
    def test_tools_available_in_all_rounds(self):
        """Test that tools remain available in all rounds"""
        self.mock_client.messages.create.side_effect = [
            MOCK_SEQUENTIAL_ROUND_1_TOOL_USE,
            MOCK_SEQUENTIAL_ROUND_2_TOOL_USE,
            MOCK_SEQUENTIAL_FINAL_RESPONSE
        ]
        
        mock_tool_manager = create_mock_tool_manager()
        mock_tools = [{"name": "search_course_content", "description": "Search content"}]
        
        self.ai_generator.generate_response(
            "Complex query",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        # Verify tools are present in first two API calls
        first_call = self.mock_client.messages.create.call_args_list[0][1]
        second_call = self.mock_client.messages.create.call_args_list[1][1]
        
        assert "tools" in first_call
        assert "tools" in second_call
        assert first_call["tools"] == mock_tools
        assert second_call["tools"] == mock_tools
    
    def test_backward_compatibility_no_tools(self):
        """Test backward compatibility for requests without tools"""
        self.mock_client.messages.create.return_value = MOCK_ANTHROPIC_RESPONSE_SIMPLE
        
        response = self.ai_generator.generate_response("What is AI?")
        
        # Should make single API call without tools
        assert self.mock_client.messages.create.call_count == 1
        call_args = self.mock_client.messages.create.call_args[1]
        assert "tools" not in call_args
        
        assert response == "This is a simple response without tools."
    
    def test_multiple_tools_in_single_response(self):
        """Test handling multiple tool calls in a single response"""
        self.mock_client.messages.create.side_effect = [
            MOCK_MULTIPLE_TOOLS_RESPONSE,
            MOCK_SEQUENTIAL_FINAL_RESPONSE
        ]
        
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = [
            "Search result 1",
            "Outline result 2"
        ]
        mock_tools = [
            {"name": "search_course_content", "description": "Search content"},
            {"name": "get_course_outline", "description": "Get outline"}
        ]
        
        response = self.ai_generator.generate_response(
            "Tell me about AI courses",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        # Should execute both tools
        assert mock_tool_manager.execute_tool.call_count == 2
        
        # Verify both tools were called
        tool_calls = mock_tool_manager.execute_tool.call_args_list
        assert tool_calls[0][0] == ('search_course_content',)
        assert tool_calls[1][0] == ('get_course_outline',)


if __name__ == "__main__":
    pytest.main([__file__])