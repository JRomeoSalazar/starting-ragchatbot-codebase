"""Tests for AIGenerator tool calling and response generation"""

import pytest
from unittest.mock import MagicMock, patch, call
from ai_generator import AIGenerator


class MockTextBlock:
    """Simple mock for text content blocks"""
    def __init__(self, text_content):
        self.type = "text"
        self.text = text_content


class TestAIGenerator:
    """Test suite for AIGenerator"""

    def test_generate_response_without_tools(self, mock_config, mock_anthropic_client):
        """Test direct response without any tools"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(mock_config.ANTHROPIC_API_KEY, mock_config.ANTHROPIC_MODEL)

            response = generator.generate_response(
                query="What is 2+2?",
                conversation_history=None,
                tools=None,
                tool_manager=None
            )

            # Verify API was called once without tools
            assert mock_anthropic_client.messages.create.call_count == 1
            call_kwargs = mock_anthropic_client.messages.create.call_args[1]

            assert 'tools' not in call_kwargs
            assert call_kwargs['messages'][0]['content'] == "What is 2+2?"
            assert response == "This is a direct answer from Claude."

    def test_generate_response_with_tools_no_use(self, mock_config, mock_anthropic_client, mock_tool_manager):
        """Test response when tools are available but not used"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(mock_config.ANTHROPIC_API_KEY, mock_config.ANTHROPIC_MODEL)

            # Mock response without tool use (end_turn)
            mock_response = MagicMock()
            mock_response.stop_reason = "end_turn"
            mock_content = MagicMock()
            mock_content.type = "text"
            mock_content.text = "General knowledge answer without tool use."
            mock_response.content = [mock_content]
            mock_anthropic_client.messages.create.return_value = mock_response

            response = generator.generate_response(
                query="What is Python?",
                conversation_history=None,
                tools=mock_tool_manager.get_tool_definitions(),
                tool_manager=mock_tool_manager
            )

            # Verify tools were provided in the call
            call_kwargs = mock_anthropic_client.messages.create.call_args[1]
            assert 'tools' in call_kwargs
            assert call_kwargs['tool_choice'] == {"type": "auto"}

            # Verify only one API call was made (no tool execution)
            assert mock_anthropic_client.messages.create.call_count == 1
            assert response == "General knowledge answer without tool use."

    def test_tool_execution_triggered(
        self,
        mock_config,
        mock_anthropic_client,
        mock_tool_manager,
        mock_anthropic_response_with_tool,
        mock_anthropic_final_response
    ):
        """Test that tool_use stop_reason triggers _handle_tool_execution"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(mock_config.ANTHROPIC_API_KEY, mock_config.ANTHROPIC_MODEL)

            # First call returns tool_use, second call returns final answer
            mock_anthropic_client.messages.create.side_effect = [
                mock_anthropic_response_with_tool,
                mock_anthropic_final_response
            ]

            response = generator.generate_response(
                query="What is MCP?",
                conversation_history=None,
                tools=mock_tool_manager.get_tool_definitions(),
                tool_manager=mock_tool_manager
            )

            # Verify two API calls were made
            assert mock_anthropic_client.messages.create.call_count == 2

            # Verify tool was executed
            mock_tool_manager.execute_tool.assert_called_once()
            call_args = mock_tool_manager.execute_tool.call_args

            # Verify correct tool and parameters
            assert call_args[0][0] == "search_course_content"
            assert call_args[1]['query'] == "MCP basics"

            # Verify final response
            assert response == "Based on the search results, MCP stands for Model Context Protocol."

    def test_tool_execution_message_flow(
        self,
        mock_config,
        mock_anthropic_client,
        mock_tool_manager,
        mock_anthropic_response_with_tool,
        mock_anthropic_final_response
    ):
        """Test correct message structure in tool execution flow"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(mock_config.ANTHROPIC_API_KEY, mock_config.ANTHROPIC_MODEL)

            # Setup response sequence
            mock_anthropic_client.messages.create.side_effect = [
                mock_anthropic_response_with_tool,
                mock_anthropic_final_response
            ]

            response = generator.generate_response(
                query="What is MCP?",
                conversation_history=None,
                tools=mock_tool_manager.get_tool_definitions(),
                tool_manager=mock_tool_manager
            )

            # Get the second API call (after tool execution)
            second_call_kwargs = mock_anthropic_client.messages.create.call_args_list[1][1]

            # Verify message structure
            messages = second_call_kwargs['messages']
            assert len(messages) == 3  # user query, assistant tool_use, user tool_result

            # Verify first message is user query
            assert messages[0]['role'] == 'user'

            # Verify second message is assistant with tool_use content
            assert messages[1]['role'] == 'assistant'
            assert messages[1]['content'] == mock_anthropic_response_with_tool.content

            # Verify third message is user with tool results
            assert messages[2]['role'] == 'user'
            assert isinstance(messages[2]['content'], list)
            assert messages[2]['content'][0]['type'] == 'tool_result'
            assert messages[2]['content'][0]['tool_use_id'] == 'tool_use_123'

    def test_infinite_loop_prevention_via_round_limit(
        self,
        mock_config,
        mock_anthropic_client,
        mock_tool_manager
    ):
        """Test that round limit prevents infinite loops even when tools are in all calls"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(mock_config.ANTHROPIC_API_KEY, mock_config.ANTHROPIC_MODEL)

            # Create responses that always request tools (simulating infinite loop scenario)
            mock_tool_response = MagicMock()
            mock_tool_response.stop_reason = "tool_use"
            mock_tool_block = MagicMock()
            mock_tool_block.type = "tool_use"
            mock_tool_block.id = "tool_use_loop"
            mock_tool_block.name = "search_course_content"
            mock_tool_block.input = {"query": "loop query"}
            # Add text content block
            mock_text_block = MockTextBlock("Response after max rounds")
            mock_tool_response.content = [mock_tool_block, mock_text_block]

            # Always return tool_use response (would cause infinite loop without round limit)
            mock_anthropic_client.messages.create.return_value = mock_tool_response

            response = generator.generate_response(
                query="Test infinite loop prevention",
                conversation_history=None,
                tools=mock_tool_manager.get_tool_definitions(),
                tool_manager=mock_tool_manager
            )

            # Should stop at 3 calls (initial + 2 rounds) despite tool_use responses
            assert mock_anthropic_client.messages.create.call_count == 3

            # All calls should have tools parameter (different from old behavior)
            for call_args in mock_anthropic_client.messages.create.call_args_list:
                assert 'tools' in call_args[1]
                assert call_args[1]['tool_choice'] == {"type": "auto"}

            # Response is returned after round limit
            assert response == "Response after max rounds"

    def test_conversation_history_integration(self, mock_config, mock_anthropic_client):
        """Test that conversation history is properly included in system prompt"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(mock_config.ANTHROPIC_API_KEY, mock_config.ANTHROPIC_MODEL)

            history = "User: What is MCP?\nAssistant: Model Context Protocol"

            response = generator.generate_response(
                query="Tell me more about it",
                conversation_history=history,
                tools=None,
                tool_manager=None
            )

            # Verify history was included in system prompt
            call_kwargs = mock_anthropic_client.messages.create.call_args[1]
            system_content = call_kwargs['system']

            assert "Previous conversation:" in system_content
            assert "What is MCP?" in system_content
            assert "Model Context Protocol" in system_content

    def test_conversation_history_absent(self, mock_config, mock_anthropic_client):
        """Test system prompt when no conversation history exists"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(mock_config.ANTHROPIC_API_KEY, mock_config.ANTHROPIC_MODEL)

            response = generator.generate_response(
                query="What is MCP?",
                conversation_history=None,
                tools=None,
                tool_manager=None
            )

            # Verify history section not in system prompt
            call_kwargs = mock_anthropic_client.messages.create.call_args[1]
            system_content = call_kwargs['system']

            assert "Previous conversation:" not in system_content

    def test_multiple_tool_calls(
        self,
        mock_config,
        mock_anthropic_client,
        mock_tool_manager,
        mock_anthropic_final_response
    ):
        """Test handling of multiple tool calls in single response"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(mock_config.ANTHROPIC_API_KEY, mock_config.ANTHROPIC_MODEL)

            # Create response with multiple tool uses
            mock_multi_tool_response = MagicMock()
            mock_multi_tool_response.stop_reason = "tool_use"

            # First tool use
            mock_tool_block_1 = MagicMock()
            mock_tool_block_1.type = "tool_use"
            mock_tool_block_1.id = "tool_use_1"
            mock_tool_block_1.name = "search_course_content"
            mock_tool_block_1.input = {"query": "MCP"}

            # Second tool use
            mock_tool_block_2 = MagicMock()
            mock_tool_block_2.type = "tool_use"
            mock_tool_block_2.id = "tool_use_2"
            mock_tool_block_2.name = "search_course_content"
            mock_tool_block_2.input = {"query": "Anthropic"}

            mock_multi_tool_response.content = [mock_tool_block_1, mock_tool_block_2]

            # Setup response sequence
            mock_anthropic_client.messages.create.side_effect = [
                mock_multi_tool_response,
                mock_anthropic_final_response
            ]

            response = generator.generate_response(
                query="Compare MCP and Anthropic",
                conversation_history=None,
                tools=mock_tool_manager.get_tool_definitions(),
                tool_manager=mock_tool_manager
            )

            # Verify both tools were executed
            assert mock_tool_manager.execute_tool.call_count == 2

            # Verify second API call has both tool results
            second_call_kwargs = mock_anthropic_client.messages.create.call_args_list[1][1]
            tool_results = second_call_kwargs['messages'][2]['content']
            assert len(tool_results) == 2
            assert tool_results[0]['tool_use_id'] == 'tool_use_1'
            assert tool_results[1]['tool_use_id'] == 'tool_use_2'

    def test_two_round_tool_execution(
        self,
        mock_config,
        mock_anthropic_client,
        mock_tool_manager,
        mock_anthropic_final_response
    ):
        """Test that Claude can make 2 sequential tool calls across separate rounds"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(mock_config.ANTHROPIC_API_KEY, mock_config.ANTHROPIC_MODEL)

            # Create first tool use response
            mock_first_tool = MagicMock()
            mock_first_tool.stop_reason = "tool_use"
            mock_tool_block_1 = MagicMock()
            mock_tool_block_1.type = "tool_use"
            mock_tool_block_1.id = "tool_use_1"
            mock_tool_block_1.name = "get_course_outline"
            mock_tool_block_1.input = {"course_name": "MCP"}
            mock_first_tool.content = [mock_tool_block_1]

            # Create second tool use response
            mock_second_tool = MagicMock()
            mock_second_tool.stop_reason = "tool_use"
            mock_tool_block_2 = MagicMock()
            mock_tool_block_2.type = "tool_use"
            mock_tool_block_2.id = "tool_use_2"
            mock_tool_block_2.name = "search_course_content"
            mock_tool_block_2.input = {"query": "lesson 4 topic"}
            mock_second_tool.content = [mock_tool_block_2]

            # Setup response sequence: tool_use → tool_use → end_turn
            mock_anthropic_client.messages.create.side_effect = [
                mock_first_tool,
                mock_second_tool,
                mock_anthropic_final_response
            ]

            response = generator.generate_response(
                query="What topic is covered in lesson 4 of MCP?",
                conversation_history=None,
                tools=mock_tool_manager.get_tool_definitions(),
                tool_manager=mock_tool_manager
            )

            # Verify 3 API calls were made (initial + 2 rounds)
            assert mock_anthropic_client.messages.create.call_count == 3

            # Verify 2 tools were executed
            assert mock_tool_manager.execute_tool.call_count == 2

            # Verify final response returned
            assert response == "Based on the search results, MCP stands for Model Context Protocol."

    def test_max_rounds_limit(
        self,
        mock_config,
        mock_anthropic_client,
        mock_tool_manager
    ):
        """Test that execution stops after 2 rounds even if Claude wants more"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(mock_config.ANTHROPIC_API_KEY, mock_config.ANTHROPIC_MODEL)

            # Create tool use responses that keep requesting tools
            mock_tool_response_1 = MagicMock()
            mock_tool_response_1.stop_reason = "tool_use"
            mock_tool_block_1 = MagicMock()
            mock_tool_block_1.type = "tool_use"
            mock_tool_block_1.id = "tool_use_1"
            mock_tool_block_1.name = "search_course_content"
            mock_tool_block_1.input = {"query": "query1"}
            mock_tool_response_1.content = [mock_tool_block_1]

            mock_tool_response_2 = MagicMock()
            mock_tool_response_2.stop_reason = "tool_use"
            mock_tool_block_2 = MagicMock()
            mock_tool_block_2.type = "tool_use"
            mock_tool_block_2.id = "tool_use_2"
            mock_tool_block_2.name = "search_course_content"
            mock_tool_block_2.input = {"query": "query2"}
            mock_tool_response_2.content = [mock_tool_block_2]

            # Third response also requests tool but should not be processed
            mock_tool_response_3 = MagicMock()
            mock_tool_response_3.stop_reason = "tool_use"
            mock_tool_block_3 = MagicMock()
            mock_tool_block_3.type = "tool_use"
            mock_tool_block_3.id = "tool_use_3"
            mock_tool_block_3.name = "search_course_content"
            mock_tool_block_3.input = {"query": "query3"}
            # Add text content block to the response
            mock_text_block = MockTextBlock("This is the response after 2 rounds")
            mock_tool_response_3.content = [mock_tool_block_3, mock_text_block]

            # Setup response sequence
            mock_anthropic_client.messages.create.side_effect = [
                mock_tool_response_1,
                mock_tool_response_2,
                mock_tool_response_3
            ]

            response = generator.generate_response(
                query="Test query",
                conversation_history=None,
                tools=mock_tool_manager.get_tool_definitions(),
                tool_manager=mock_tool_manager
            )

            # Verify only 3 API calls made (initial + 2 rounds)
            assert mock_anthropic_client.messages.create.call_count == 3

            # Verify only 2 tools executed (not 3)
            assert mock_tool_manager.execute_tool.call_count == 2

            # Verify we got the response from the 3rd call
            assert response == "This is the response after 2 rounds"

    def test_early_termination_after_one_round(
        self,
        mock_config,
        mock_anthropic_client,
        mock_tool_manager,
        mock_anthropic_response_with_tool
    ):
        """Test that execution stops after 1 round if Claude doesn't need more"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(mock_config.ANTHROPIC_API_KEY, mock_config.ANTHROPIC_MODEL)

            # Second response is end_turn (no more tools needed)
            mock_final = MagicMock()
            mock_final.stop_reason = "end_turn"
            mock_content = MagicMock()
            mock_content.type = "text"
            mock_content.text = "Answer after one tool call"
            mock_final.content = [mock_content]

            # Setup response sequence: tool_use → end_turn
            mock_anthropic_client.messages.create.side_effect = [
                mock_anthropic_response_with_tool,
                mock_final
            ]

            response = generator.generate_response(
                query="Simple query needing one tool",
                conversation_history=None,
                tools=mock_tool_manager.get_tool_definitions(),
                tool_manager=mock_tool_manager
            )

            # Verify only 2 API calls (initial + 1 round)
            assert mock_anthropic_client.messages.create.call_count == 2

            # Verify only 1 tool executed
            assert mock_tool_manager.execute_tool.call_count == 1

            # Verify response
            assert response == "Answer after one tool call"

    def test_tools_parameter_in_intermediate_calls(
        self,
        mock_config,
        mock_anthropic_client,
        mock_tool_manager,
        mock_anthropic_response_with_tool,
        mock_anthropic_final_response
    ):
        """Test that tools parameter is included in intermediate API calls"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(mock_config.ANTHROPIC_API_KEY, mock_config.ANTHROPIC_MODEL)

            # Setup response sequence
            mock_anthropic_client.messages.create.side_effect = [
                mock_anthropic_response_with_tool,
                mock_anthropic_final_response
            ]

            response = generator.generate_response(
                query="Test query",
                conversation_history=None,
                tools=mock_tool_manager.get_tool_definitions(),
                tool_manager=mock_tool_manager
            )

            # Get both API calls
            first_call = mock_anthropic_client.messages.create.call_args_list[0][1]
            second_call = mock_anthropic_client.messages.create.call_args_list[1][1]

            # Both calls should have tools parameter
            assert 'tools' in first_call
            assert first_call['tool_choice'] == {"type": "auto"}
            assert 'tools' in second_call
            assert second_call['tool_choice'] == {"type": "auto"}

    def test_message_accumulation_across_rounds(
        self,
        mock_config,
        mock_anthropic_client,
        mock_tool_manager,
        mock_anthropic_final_response
    ):
        """Test that messages accumulate correctly across multiple rounds"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(mock_config.ANTHROPIC_API_KEY, mock_config.ANTHROPIC_MODEL)

            # First tool use
            mock_first_tool = MagicMock()
            mock_first_tool.stop_reason = "tool_use"
            mock_tool_block_1 = MagicMock()
            mock_tool_block_1.type = "tool_use"
            mock_tool_block_1.id = "tool_use_1"
            mock_tool_block_1.name = "search_course_content"
            mock_tool_block_1.input = {"query": "first"}
            mock_first_tool.content = [mock_tool_block_1]

            # Second tool use
            mock_second_tool = MagicMock()
            mock_second_tool.stop_reason = "tool_use"
            mock_tool_block_2 = MagicMock()
            mock_tool_block_2.type = "tool_use"
            mock_tool_block_2.id = "tool_use_2"
            mock_tool_block_2.name = "search_course_content"
            mock_tool_block_2.input = {"query": "second"}
            mock_second_tool.content = [mock_tool_block_2]

            mock_anthropic_client.messages.create.side_effect = [
                mock_first_tool,
                mock_second_tool,
                mock_anthropic_final_response
            ]

            response = generator.generate_response(
                query="Test query",
                conversation_history=None,
                tools=mock_tool_manager.get_tool_definitions(),
                tool_manager=mock_tool_manager
            )

            # Check final API call message structure
            final_call = mock_anthropic_client.messages.create.call_args_list[2][1]
            messages = final_call['messages']

            # Should have: user query, assistant tool_use #1, user tool_results #1,
            #              assistant tool_use #2, user tool_results #2
            assert len(messages) == 5

            # Verify structure
            assert messages[0]['role'] == 'user'  # Original query
            assert messages[1]['role'] == 'assistant'  # First tool use
            assert messages[1]['content'] == mock_first_tool.content
            assert messages[2]['role'] == 'user'  # First tool results
            assert messages[3]['role'] == 'assistant'  # Second tool use
            assert messages[3]['content'] == mock_second_tool.content
            assert messages[4]['role'] == 'user'  # Second tool results

    def test_tool_error_during_second_round(
        self,
        mock_config,
        mock_anthropic_client,
        mock_tool_manager,
        mock_anthropic_response_with_tool
    ):
        """Test graceful handling when tool execution fails in second round"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(mock_config.ANTHROPIC_API_KEY, mock_config.ANTHROPIC_MODEL)

            # Second tool use
            mock_second_tool = MagicMock()
            mock_second_tool.stop_reason = "tool_use"
            mock_tool_block = MagicMock()
            mock_tool_block.type = "tool_use"
            mock_tool_block.id = "tool_use_2"
            mock_tool_block.name = "search_course_content"
            mock_tool_block.input = {"query": "bad query"}
            mock_second_tool.content = [mock_tool_block]

            # Final response after error
            mock_final = MagicMock()
            mock_final.stop_reason = "end_turn"
            mock_content = MagicMock()
            mock_content.type = "text"
            mock_content.text = "Response with error info"
            mock_final.content = [mock_content]

            mock_anthropic_client.messages.create.side_effect = [
                mock_anthropic_response_with_tool,
                mock_second_tool,
                mock_final
            ]

            # First tool succeeds, second tool fails
            mock_tool_manager.execute_tool.side_effect = [
                "First tool result",
                "Error: Tool execution failed"
            ]

            response = generator.generate_response(
                query="Test query",
                conversation_history=None,
                tools=mock_tool_manager.get_tool_definitions(),
                tool_manager=mock_tool_manager
            )

            # Should complete despite error (error is passed to Claude as tool result)
            assert mock_tool_manager.execute_tool.call_count == 2
            assert response == "Response with error info"

    def test_api_parameters(self, mock_config, mock_anthropic_client):
        """Test that base API parameters are correctly set"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(mock_config.ANTHROPIC_API_KEY, mock_config.ANTHROPIC_MODEL)

            response = generator.generate_response(
                query="Test query",
                conversation_history=None,
                tools=None,
                tool_manager=None
            )

            call_kwargs = mock_anthropic_client.messages.create.call_args[1]

            # Verify base parameters
            assert call_kwargs['model'] == mock_config.ANTHROPIC_MODEL
            assert call_kwargs['temperature'] == 0
            assert call_kwargs['max_tokens'] == 800
