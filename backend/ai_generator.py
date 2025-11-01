from typing import Any, Dict, List, Optional

import anthropic


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive tools for course information.

Tool Usage Guidelines:
- **Course outline queries**: Use the get_course_outline tool for questions about course structure, lesson lists, or course overview
  - Returns: Course title, course link, instructor, and complete list of lessons with their numbers, titles, and links
  - Example queries: "What lessons are in the MCP course?", "Show me the outline for X course", "What topics are covered in Y?"

- **Content search queries**: Use the search_course_content tool for questions about specific course content or detailed educational materials
  - Returns: Relevant content from course lessons
  - Example queries: "What does lesson 3 say about X?", "Explain the concept of Y from course Z"

- **Multi-step tool usage**: You can make up to 2 tool calls across separate reasoning steps if needed
  - Common patterns:
    * Get course outline first, then search for specific lesson content based on results
    * Search one course, then search another course to compare information
    * Retrieve metadata first, then use it to refine a content search
  - Always synthesize a complete final answer after all tool calls are done
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course structure questions**: Use get_course_outline tool first, then present the information clearly
- **Course content questions**: Use search_course_content tool first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool usage explanations, or question-type analysis
 - Do not mention "based on the tool results" or "I used the tool"

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
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
        max_tool_rounds: int = 2,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_tool_rounds: Maximum number of sequential tool call rounds (default: 2)

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content,
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get response from Claude
        response = self.client.messages.create(**api_params)

        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(
                response, api_params, tool_manager, max_tool_rounds
            )

        # Return direct response
        return response.content[0].text

    def _handle_tool_execution(
        self,
        initial_response,
        base_params: Dict[str, Any],
        tool_manager,
        max_tool_rounds: int,
    ):
        """
        Handle execution of tool calls with support for sequential rounds.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            max_tool_rounds: Maximum number of sequential tool call rounds

        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()

        # Track current response and round counter
        current_response = initial_response
        rounds_completed = 0

        # Loop for up to max_tool_rounds
        while (
            rounds_completed < max_tool_rounds
            and current_response.stop_reason == "tool_use"
        ):
            rounds_completed += 1

            # Add AI's tool use response to messages
            messages.append({"role": "assistant", "content": current_response.content})

            # Execute all tool calls and collect results
            tool_results = []
            for content_block in current_response.content:
                if content_block.type == "tool_use":
                    tool_result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result,
                        }
                    )

            # Add tool results as single message
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            # Prepare next API call WITH tools (allows Claude to make another tool call if needed)
            next_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"],
                "tools": base_params["tools"],
                "tool_choice": base_params["tool_choice"],
            }

            # Get next response
            current_response = self.client.messages.create(**next_params)

        # Return final response text
        # Handle case where final response might still be tool_use (after hitting round limit)
        for content_block in current_response.content:
            if getattr(content_block, "type", None) == "text":
                return content_block.text

        # If no text block found (shouldn't happen in practice), return empty string
        return ""
