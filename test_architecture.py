#!/usr/bin/env python3
"""
Test script for the Tax Chatbot architecture.

This script demonstrates how to use the clean architecture and tests various features.
"""

import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
load_dotenv()

from src.agent import TaxChatbot
from src.llm import MockLLMClient


def test_basic_chat():
    """Test basic chat functionality."""
    print("=== Testing Basic Chat ===")
    
    # Use mock client for testing (replace with OpenAIClient for real testing)
    mock_responses = [
        "Hallo! Ik ben een Nederlandse belastingchatbot. Ik kan u helpen met belastingvragen.",
        "Ik spreek Nederlands en kan Nederlandse belastingvragen beantwoorden.",
    ]
    mock_client = MockLLMClient(responses=mock_responses)
    
    # Create chatbot
    chatbot = TaxChatbot(llm_client=mock_client, session_id="test_session")
    
    # Test general questions
    print("\nUser: Wat kun je doen?")
    response = chatbot.process_message("Wat kun je doen?")
    print(f"Bot: {response}")
    
    print("\nUser: Welke talen spreek je?")
    response = chatbot.process_message("Welke talen spreek je?")
    print(f"Bot: {response}")
    
    return chatbot


def test_session_management():
    """Test session management features."""
    print("\n=== Testing Session Management ===")
    
    chatbot = TaxChatbot(session_id="test_session_2")
    
    # Get session info
    info = chatbot.get_session_info()
    print(f"Session info: {info}")
    
    # Test commands
    print("\nUser: show status")
    response = chatbot.process_message("show status")
    print(f"Bot: {response}")
    
    print("\nUser: reset")
    response = chatbot.process_message("reset")
    print(f"Bot: {response}")


def test_tools():
    """Test tool functionality."""
    print("\n=== Testing Tools ===")
    
    chatbot = TaxChatbot(session_id="test_tools")
    
    # List available tools
    tools = chatbot.list_available_tools()
    print(f"Available tools: {tools}")
    
    # Test tool validation
    validation_errors = chatbot.tool_manager.validate_tools()
    if validation_errors:
        print(f"Tool validation errors: {validation_errors}")
    else:
        print("All tools passed validation ✓")


def test_commands():
    """Test command processing."""
    print("\n=== Testing Commands ===")
    
    chatbot = TaxChatbot(session_id="test_commands")
    
    # List available commands
    commands = chatbot.list_available_commands()
    print(f"Available command patterns: {commands}")
    
    # Test various commands
    test_commands = [
        "toon bronnen",
        "verwijder wetgeving",
        "herformuleer antwoord",
        "clear session"
    ]
    
    for cmd in test_commands:
        print(f"\nUser: {cmd}")
        response = chatbot.process_message(cmd)
        print(f"Bot: {response}")


def test_real_openai():
    """Test with real OpenAI (requires API key)."""
    print("\n=== Testing with Real OpenAI ===")
    
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠ Skipping OpenAI test - no API key found")
        return
    
    try:
        from src.llm import OpenAIClient
        
        # Create real client
        client = OpenAIClient()
        chatbot = TaxChatbot(llm_client=client, session_id="real_test")
        
        # Test general question
        print("\nUser: Hallo, wat kun je doen?")
        response = chatbot.process_message("Hallo, wat kun je doen?")
        print(f"Bot: {response}")
        
        # Test tax question (this should trigger tool usage)
        print("\nUser: Wat is het BTW tarief?")
        response = chatbot.process_message("Wat is het BTW tarief?")
        print(f"Bot: {response}")
        
        # Show session info
        info = chatbot.get_session_info()
        print(f"\nSession after tax question: {info}")
        
        # Test confirmation step if sources were shown
        if "Zijn deze bronnen correct" in response:
            print("\n=== Testing Source Confirmation ===")
            print("User: ja")
            confirmation_response = chatbot.process_message("ja")
            print(f"Bot: {confirmation_response}")
            
            # Verify generate_tax_answer was used
            if len(confirmation_response) > 200:
                print("✅ Confirmation worked - got detailed answer")
            else:
                print(f"❌ Confirmation failed - response too short ({len(confirmation_response)} chars)")
                print(f"Response: {confirmation_response}")
        
    except Exception as e:
        print(f"Error testing with OpenAI: {e}")


def main():
    """Run all tests."""
    print("Testing Tax Chatbot Architecture")
    print("=" * 50)
    
    try:
        # Basic tests
        chatbot = test_basic_chat()
        test_session_management()
        test_tools()
        test_commands()
        
        # Real OpenAI test (optional)
        test_real_openai()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        
        # Cleanup
        removed = chatbot.cleanup_old_sessions(hours=0)  # Remove all sessions
        print(f"Cleaned up {removed} test sessions")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()