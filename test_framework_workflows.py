#!/usr/bin/env python3
"""
Comprehensive workflow tests for LangChain and LlamaIndex implementations.
Tests the complete compliance workflow: question → sources → confirmation → final answer
"""

import sys
import os
import importlib.util

def test_original_workflow():
    """Test the original implementation workflow."""
    print("=" * 60)
    print("TESTING ORIGINAL IMPLEMENTATION WORKFLOW")
    print("=" * 60)
    
    try:
        sys.path.insert(0, 'src')
        from agent import TaxChatbot
        
        chatbot = TaxChatbot(session_id='original_test')
        
        print("\n=== Step 1: Ask BTW question ===")
        response1 = chatbot.process_message('wat is het btw tarief?')
        print(f"Response 1: {response1}")
        
        # Check if workflow is followed
        if "Ik vond de volgende bronnen" in response1 and "Zijn deze bronnen correct" in response1:
            print("✅ Original: Shows sources and asks for confirmation")
            
            print("\n=== Step 2: Confirm sources ===")
            response2 = chatbot.process_message('ja')
            print(f"Response 2 length: {len(response2)} chars")
            print(f"Response 2: {response2[:200]}...")
            
            if len(response2) > 200:  # Detailed answer
                print("✅ Original: Generates detailed answer after confirmation")
                return True
            else:
                print("❌ Original: Failed to generate detailed answer")
                return False
        else:
            print("❌ Original: Failed to show sources and ask for confirmation")
            return False
            
    except Exception as e:
        print(f"❌ Original test failed: {str(e)}")
        return False


def test_langchain_workflow():
    """Test the LangChain implementation workflow."""
    print("\n" + "=" * 60)
    print("TESTING LANGCHAIN IMPLEMENTATION WORKFLOW")
    print("=" * 60)
    
    try:
        sys.path.insert(0, 'src_langchain')
        from agent import LangChainTaxChatbot
        
        chatbot = LangChainTaxChatbot(session_id='langchain_test')
        
        print("\n=== Step 1: Ask BTW question ===")
        response1 = chatbot.process_message('wat is het btw tarief?')
        print(f"Response 1: {response1}")
        
        # Check if workflow is followed
        if "bronnen" in response1.lower() and ("correct" in response1.lower() or "klopt" in response1.lower()):
            print("✅ LangChain: Shows sources and asks for confirmation")
            
            print("\n=== Step 2: Confirm sources ===")
            response2 = chatbot.process_message('ja')
            print(f"Response 2 length: {len(response2)} chars")
            print(f"Response 2: {response2[:200]}...")
            
            if len(response2) > 200:  # Detailed answer
                print("✅ LangChain: Generates detailed answer after confirmation")
                return True
            else:
                print("❌ LangChain: Failed to generate detailed answer")
                print(f"Full response: {response2}")
                return False
        else:
            print("❌ LangChain: Failed to show sources and ask for confirmation")
            return False
            
    except Exception as e:
        print(f"❌ LangChain test failed: {str(e)}")
        return False


def test_llamaindex_workflow():
    """Test the LlamaIndex implementation workflow."""
    print("\n" + "=" * 60)
    print("TESTING LLAMAINDEX IMPLEMENTATION WORKFLOW")
    print("=" * 60)
    
    try:
        sys.path.insert(0, 'src_llamaindex')
        from agent import LlamaIndexTaxChatbot
        
        chatbot = LlamaIndexTaxChatbot(session_id='llamaindex_test')
        
        print("\n=== Step 1: Ask BTW question ===")
        response1 = chatbot.process_message('wat is het btw tarief?')
        print(f"Response 1: {response1}")
        
        # Check if workflow is followed
        if "bronnen" in response1.lower() and ("correct" in response1.lower() or "klopt" in response1.lower()):
            print("✅ LlamaIndex: Shows sources and asks for confirmation")
            
            print("\n=== Step 2: Confirm sources ===")
            response2 = chatbot.process_message('ja')
            print(f"Response 2 length: {len(response2)} chars")
            print(f"Response 2: {response2[:200]}...")
            
            if len(response2) > 200:  # Detailed answer
                print("✅ LlamaIndex: Generates detailed answer after confirmation")
                return True
            else:
                print("❌ LlamaIndex: Failed to generate detailed answer")
                print(f"Full response: {response2}")
                return False
        else:
            print("❌ LlamaIndex: Failed to show sources and ask for confirmation")
            print("Note: LlamaIndex may still have architecture limitations")
            return False
            
    except Exception as e:
        print(f"❌ LlamaIndex test failed: {str(e)}")
        print("Note: This may be due to LlamaIndex import/architecture issues")
        return False


def test_session_context():
    """Test session context tracking across all implementations."""
    print("\n" + "=" * 60)
    print("TESTING SESSION CONTEXT TRACKING")
    print("=" * 60)
    
    results = []
    
    # Test original implementation session tracking
    try:
        sys.path.insert(0, 'src')
        from agent import TaxChatbot
        
        chatbot = TaxChatbot(session_id='context_test')
        chatbot.process_message('wat is het btw tarief?')
        
        session_info = chatbot.get_session_info()
        if session_info.get('sources'):
            print("✅ Original: Session context tracking works")
            results.append(True)
        else:
            print("❌ Original: No session context tracked")
            results.append(False)
    except Exception as e:
        print(f"❌ Original session test failed: {str(e)}")
        results.append(False)
    
    # Test LangChain session tracking
    try:
        sys.path.insert(0, 'src_langchain')
        from agent import LangChainTaxChatbot
        
        chatbot = LangChainTaxChatbot(session_id='langchain_context_test')
        chatbot.process_message('wat is het btw tarief?')
        
        session_info = chatbot.get_session_info()
        if session_info.get('sources'):
            print("✅ LangChain: Session context tracking works")
            results.append(True)
        else:
            print("⚠️ LangChain: Limited session context tracking")
            results.append(False)
    except Exception as e:
        print(f"❌ LangChain session test failed: {str(e)}")
        results.append(False)
    
    # Test LlamaIndex session tracking
    try:
        sys.path.insert(0, 'src_llamaindex')
        from agent import LlamaIndexTaxChatbot
        
        chatbot = LlamaIndexTaxChatbot(session_id='llamaindex_context_test')
        chatbot.process_message('wat is het btw tarief?')
        
        session_info = chatbot.get_session_info()
        if session_info.get('sources'):
            print("✅ LlamaIndex: Session context tracking works")
            results.append(True)
        else:
            print("⚠️ LlamaIndex: Limited session context tracking")
            results.append(False)
    except Exception as e:
        print(f"❌ LlamaIndex session test failed: {str(e)}")
        results.append(False)
    
    return all(results)


def main():
    """Run all workflow tests and provide summary."""
    print("FRAMEWORK WORKFLOW COMPLIANCE TESTING")
    print("Testing compliance workflow: question → sources → confirmation → answer")
    
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️ WARNING: No OPENAI_API_KEY found. Tests may fail.")
        print("Set your API key to run complete tests.")
        return
    
    results = []
    
    # Test all implementations
    results.append(("Original", test_original_workflow()))
    results.append(("LangChain", test_langchain_workflow()))
    results.append(("LlamaIndex", test_llamaindex_workflow()))
    
    # Test session context
    session_result = test_session_context()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for framework, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{framework:12} Workflow: {status}")
    
    session_status = "✅ PASS" if session_result else "⚠️ PARTIAL"
    print(f"{'All':12} Sessions: {session_status}")
    
    # Overall assessment
    all_passed = all(result for _, result in results) and session_result
    overall_status = "✅ ALL TESTS PASSED" if all_passed else "❌ SOME TESTS FAILED"
    
    print(f"\nOVERALL: {overall_status}")
    
    if not all_passed:
        print("\nNote: Framework limitations may prevent full compliance workflow implementation.")
        print("Check individual test outputs for specific issues.")


if __name__ == "__main__":
    main()