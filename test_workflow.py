#!/usr/bin/env python3
"""
Test the complete workflow including source confirmation.
"""

import sys
sys.path.append('src')

from agent import TaxChatbot
from llm import MockLLMClient

def test_workflow():
    """Test the complete tax question workflow."""
    
    print("Testing Complete Workflow")
    print("=" * 50)
    
    # Test with real OpenAI client
    try:
        chatbot = TaxChatbot(session_id='workflow_test')
        
        print("\n=== Step 1: Ask BTW question ===")
        response1 = chatbot.process_message('wat is het btw tarief')
        print(f"Response 1: {response1}")
        
        # Check if sources were collected
        session = chatbot.session_manager.get_session('workflow_test')
        print(f"Sources after question: {list(session.sources.keys())}")
        
        print("\n=== Step 2: Confirm sources ===") 
        response2 = chatbot.process_message('ja')
        print(f"Response 2: {response2}")
        
        # Check final state
        session = chatbot.session_manager.get_session('workflow_test')
        print(f"Final sources: {list(session.sources.keys())}")
        print(f"Session state: {session.state.value}")
        
        print("\n✅ Workflow test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    test_workflow()