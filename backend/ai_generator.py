import anthropic
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class ConversationState:
    """Manages conversation state across multiple API rounds"""
    messages: List[Dict[str, Any]]
    system_prompt: str
    round_number: int
    api_params_base: Dict[str, Any]


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Maximum rounds for sequential tool calling
    MAX_ROUNDS = 2
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive search tools for course information.

Available Tools:
1. **Course Content Search** - For questions about specific course content or detailed educational materials
2. **Course Outline** - For questions about course structure, lessons list, or course overview

Tool Usage Guidelines:
- **Content questions**: Use the course content search tool for specific lesson content, concepts, or detailed materials
- **Outline questions**: Use the course outline tool for questions about:
  - Course structure or organization
  - Complete lesson lists
  - Course titles, links, and overview information
  - "What lessons are in..." or "Show me the outline of..." type queries
- **Sequential reasoning**: You can use tools multiple times across different reasoning steps to build comprehensive answers
- **Multi-step queries**: For complex questions requiring multiple searches or comparisons, use tools sequentially based on previous results
- Synthesize tool results into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course-specific questions**: Use appropriate tool first, then answer
- **Course outline responses**: When using the outline tool, present the complete course information including:
  - Course title and instructor
  - Course link
  - Complete numbered lesson list with titles
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the tool"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        Supports sequential tool calling across multiple API rounds.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Initialize conversation state
        state = ConversationState(
            messages=[{"role": "user", "content": query}],
            system_prompt=system_content,
            round_number=1,
            api_params_base={
                **self.base_params,
                "system": system_content
            }
        )
        
        # Execute conversation loop with sequential tool calling
        if tools and tool_manager:
            return self._execute_conversation_loop(state, tools, tool_manager)
        else:
            # Fallback to single API call for non-tool requests or missing tool manager
            api_params = {
                **state.api_params_base,
                "messages": state.messages
            }
            
            # Add tools if available (for backward compatibility)
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = {"type": "auto"}
            
            response = self.client.messages.create(**api_params)
            
            # Handle tool use in legacy mode (single round)
            if response.stop_reason == "tool_use" and tool_manager:
                return self._handle_tool_execution(response, api_params, tool_manager)
            
            return response.content[0].text
    
    def _execute_conversation_loop(self, state: ConversationState, tools: List, tool_manager) -> str:
        """
        Execute sequential tool calling conversation loop.
        
        Args:
            state: Current conversation state
            tools: Available tools for the AI
            tool_manager: Manager to execute tools
            
        Returns:
            Final response text after sequential tool execution
        """
        
        for round_number in range(1, self.MAX_ROUNDS + 1):
            state.round_number = round_number
            
            # Prepare API parameters for this round
            api_params = {
                **state.api_params_base,
                "messages": state.messages.copy(),
                "tools": tools,
                "tool_choice": {"type": "auto"}
            }
            
            # Make API call
            try:
                response = self.client.messages.create(**api_params)
            except Exception as e:
                # Handle API errors gracefully
                return f"I encountered an error while processing your request: {str(e)}"
            
            # Check termination conditions
            if response.stop_reason != "tool_use":
                # Natural completion - Claude doesn't want to use tools
                return response.content[0].text
            
            if round_number == self.MAX_ROUNDS:
                # Max rounds reached - force final response without tools
                return self._get_final_response_without_tools(state, response)
            
            # Execute tools and continue to next round
            try:
                self._execute_tools_and_update_state(state, response, tool_manager)
            except Exception as e:
                # Handle tool execution errors gracefully
                return f"I encountered an error while using the search tools: {str(e)}"
        
        # Should never reach here, but fallback
        return "I was unable to complete the request."
    
    def _execute_tools_and_update_state(self, state: ConversationState, response, tool_manager):
        """
        Execute tools from the response and update conversation state.
        
        Args:
            state: Current conversation state to update
            response: API response containing tool use
            tool_manager: Manager to execute tools
        """
        # Add assistant's tool use response to conversation
        state.messages.append({"role": "assistant", "content": response.content})
        
        # Execute all tool calls and collect results
        tool_results = []
        for content_block in response.content:
            if content_block.type == "tool_use":
                tool_result = tool_manager.execute_tool(
                    content_block.name, 
                    **content_block.input
                )
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })
        
        # Add tool results to conversation
        if tool_results:
            state.messages.append({"role": "user", "content": tool_results})
    
    def _get_final_response_without_tools(self, state: ConversationState, last_response) -> str:
        """
        Get final response when max rounds reached but Claude still wants tools.
        
        Args:
            state: Current conversation state
            last_response: Last response that wanted to use tools
            
        Returns:
            Final response text
        """
        # Add the tool use response to conversation
        state.messages.append({"role": "assistant", "content": last_response.content})
        
        # Add a user message indicating this is the final round
        final_instruction = "Please provide your final response based on the information available. No more tools can be used."
        state.messages.append({"role": "user", "content": final_instruction})
        
        # Make final API call without tools
        final_params = {
            **state.api_params_base,
            "messages": state.messages
        }
        
        try:
            final_response = self.client.messages.create(**final_params)
            return final_response.content[0].text
        except Exception as e:
            return f"I was unable to provide a final response: {str(e)}"
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Legacy method for backward compatibility.
        Handles single-round tool execution for non-sequential calls.
        
        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            
        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()
        
        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})
        
        # Execute all tool calls and collect results
        tool_results = []
        for content_block in initial_response.content:
            if content_block.type == "tool_use":
                tool_result = tool_manager.execute_tool(
                    content_block.name, 
                    **content_block.input
                )
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })
        
        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        
        # Prepare final API call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"]
        }
        
        # Get final response
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text