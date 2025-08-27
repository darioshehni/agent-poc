#!/usr/bin/env python3
"""
Terminal interface for the Tax Chatbot.
Run this file to interact with the agent through your terminal.

Usage:
    python terminal_chat.py                    # Use original implementation (default)
    python terminal_chat.py --framework original
    python terminal_chat.py --framework langchain
    python terminal_chat.py --framework llamaindex
"""

import sys
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_chatbot(framework: str):
    """Initialize chatbot based on selected framework."""
    if framework == "original":
        # Add original src to path
        src_path = Path(__file__).parent / "src"
        sys.path.insert(0, str(src_path))
        
        from agent import TaxChatbot
        from llm import OpenAIClient
        
        llm_client = OpenAIClient()
        return TaxChatbot(llm_client=llm_client, session_id="terminal_session")
        
    elif framework == "langchain":
        # Add LangChain src to path
        src_path = Path(__file__).parent / "src_langchain"
        sys.path.insert(0, str(src_path))
        
        from agent import LangChainTaxChatbot
        return LangChainTaxChatbot(session_id="terminal_session")
        
    elif framework == "llamaindex":
        # Add LlamaIndex src to path  
        src_path = Path(__file__).parent / "src_llamaindex"
        sys.path.insert(0, str(src_path))
        
        from agent import LlamaIndexTaxChatbot
        return LlamaIndexTaxChatbot(session_id="terminal_session")
        
    else:
        raise ValueError(f"Unknown framework: {framework}")


def main():
    """Main terminal interface."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Dutch Tax Chatbot - Framework Comparison")
    parser.add_argument(
        "--framework",
        choices=["original", "langchain", "llamaindex"], 
        default="original",
        help="Choose which framework implementation to use (default: original)"
    )
    args = parser.parse_args()
    
    try:
        # Initialize chatbot based on framework choice
        chatbot = get_chatbot(args.framework)
        framework_name = args.framework.title()
        
    except Exception as e:
        print(f"❌ Error initializing {args.framework} chatbot: {e}")
        print("Make sure your OPENAI_API_KEY is set in .env file")
        if args.framework != "original":
            print(f"Also ensure you have installed the {args.framework} dependencies from requirements.txt")
        return
    
    print("=" * 70)
    print(f"🏛️  NEDERLANDSE BELASTING CHATBOT ({framework_name})")
    print("=" * 70)
    print("Welkom! Ik kan u helpen met Nederlandse belastingvragen.")
    print("Type 'quit', 'exit', of 'stop' om te stoppen.")
    print("Type 'help' voor meer informatie over wat ik kan doen.")
    print(f"Framework: {framework_name}")
    print("-" * 70)
    
    while True:
        try:
            # Get user input
            user_input = input("\n💬 U: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'stop', 'bye']:
                print("\n👋 Bedankt voor het gebruiken van de belasting chatbot. Tot ziens!")
                break
            
            # Skip empty input
            if not user_input:
                continue
            
            # Process message
            response = chatbot.process_message(user_input)
            
            # Display response
            print(f"\n🤖 TESS: {response}")
            
        except KeyboardInterrupt:
            print("\n\n👋 Chatbot gestopt. Tot ziens!")
            break
        except Exception as e:
            print(f"\n❌ Er is een fout opgetreden: {e}")
            print("Probeer het opnieuw of herstart de chatbot.")


if __name__ == "__main__":
    main()