#!/usr/bin/env python3
"""
Terminal interface for the Tax Chatbot.
Run this file to interact with the agent through your terminal.
"""

import sys
import os
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from agent import TaxChatbot
from llm import OpenAIClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def main():
    """Main terminal interface."""
    try:
        # Initialize with real OpenAI client
        llm_client = OpenAIClient()
        chatbot = TaxChatbot(llm_client=llm_client, session_id="terminal_session")
    except Exception as e:
        print(f"❌ Error initializing chatbot: {e}")
        print("Make sure your OPENAI_API_KEY is set in .env file")
        return
    
    print("=" * 60)
    print("🏛️  NEDERLANDSE BELASTING CHATBOT")
    print("=" * 60)
    print("Welkom! Ik kan u helpen met Nederlandse belastingvragen.")
    print("Type 'quit', 'exit', of 'stop' om te stoppen.")
    print("Type 'help' voor meer informatie over wat ik kan doen.")
    print("-" * 60)
    
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