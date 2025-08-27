#!/usr/bin/env python3
"""
Terminal interface for the Tax Chatbot.
Run this file to interact with the agent through your terminal.

Usage:
    python terminal_chat.py                    # Start the original implementation
"""

import sys
import os
import argparse
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_chatbot(session_id: str):
    """Initialize the original chatbot implementation."""
    # Add original src to path
    src_path = Path(__file__).parent / "src"
    sys.path.insert(0, str(src_path))

    from agent import TaxChatbot
    from llm import OpenAIClient

    llm_client = OpenAIClient()
    return TaxChatbot(llm_client=llm_client, session_id=session_id)


def main():
    """Main terminal interface."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Tax Chatbot")
    parser.add_argument(
        "--session",
        default="",
        help="Optional session ID to resume or share. If omitted, a new one is generated."
    )
    args = parser.parse_args()
    
    try:
        # Resolve session id
        session_id = args.session.strip()
        if not session_id:
            session_id = f"term-{uuid.uuid4().hex[:8]}"
            # Store last terminal session id
            try:
                base = Path("data/sessions")
                base.mkdir(parents=True, exist_ok=True)
                (base / "terminal_last.json").write_text(session_id, encoding="utf-8")
            except Exception:
                pass

        chatbot = get_chatbot(session_id)

    except Exception as e:
        print(f"❌ Error initializing chatbot: {e}")
        print("Make sure your OPENAI_API_KEY is set in .env file")
    
    print("=" * 70)
    print("🏛️  NEDERLANDSE BELASTING CHATBOT (ORIGINAL)")
    print("=" * 70)
    print("Welkom! Ik kan u helpen met Nederlandse belastingvragen.")
    print("Type 'quit', 'exit', of 'stop' om te stoppen.")
    # Commands removed; interact naturally with the agent.
    print(f"Session ID: {session_id}")
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
