#!/usr/bin/env python3
"""
Terminal WebSocket client for the Tax Chatbot.

Connects to the API WebSocket, sends one message per connection, receives the
response, and prints it. The server updates and persists the dossier after the
reply is sent, so you can resume by reusing the same dossier_id.

Usage:
    python terminal_chat.py --dossier <optional_dossier_id>

Environment:
    TAX_WS_URL (default: ws://localhost:8000/ws)
"""

import os
import argparse
import uuid
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    import websockets
except ImportError:
    raise SystemExit("The 'websockets' package is required. Install with: pip install websockets")


async def send_ws_message(url: str, message: str, dossier_id: str) -> dict:
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({"message": message, "dossier_id": dossier_id}))
        raw = await ws.recv()
        return json.loads(raw)


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Tax Chatbot (WebSocket client)")
    parser.add_argument(
        "--dossier",
        default="",
        help="Optional dossier ID to resume or share. If omitted, a new one is generated."
    )
    parser.add_argument(
        "--url",
        default=os.getenv("TAX_WS_URL", "ws://localhost:8000/ws"),
        help="WebSocket URL (default: ws://localhost:8000/ws)"
    )
    args = parser.parse_args()

    # Resolve session id
    dossier_id = args.dossier.strip()
    if not dossier_id:
        dossier_id = f"dos-{uuid.uuid4().hex[:8]}"
        # Store last terminal session id (optional)
        try:
            base = Path("data/sessions")
            base.mkdir(parents=True, exist_ok=True)
            (base / "terminal_last.json").write_text(dossier_id, encoding="utf-8")
        except Exception:
            pass

    print("=" * 70)
    print("🏛️  NEDERLANDSE BELASTING CHATBOT (WS)")
    print("=" * 70)
    print("Welkom! Ik kan u helpen met Nederlandse belastingvragen.")
    print("Type 'quit', 'exit', of 'stop' om te stoppen.")
    print(f"Dossier ID: {dossier_id}")
    print(f"WS URL: {args.url}")
    print("-" * 70)

    while True:
        try:
            # Get user input
            user_input = input("\n💬 U: ").strip()

            # Check for exit commands
            if user_input.lower() in ["quit", "exit", "stop", "bye"]:
                print("\n👋 Bedankt voor het gebruiken van de belasting chatbot. Tot ziens!")
                break

            if not user_input:
                continue

            # Send over WebSocket and receive one response
            resp = await send_ws_message(args.url, user_input, dossier_id)

            if resp.get("status") != "success":
                print(f"\n❌ Fout: {resp.get('error') or 'onbekende fout'}")
                continue

            # Update dossier_id from server (in case it was generated there)
            dossier_id = resp.get("dossier_id") or dossier_id

            # Display response
            print(f"\n🤖 TESS: {resp.get('response', '')}")

        except KeyboardInterrupt:
            print("\n\n👋 Chatbot gestopt. Tot ziens!")
            break
        except Exception as e:
            print(f"\n❌ Er is een fout opgetreden: {e}")
            print("Probeer het opnieuw of herstart de chatbot.")


if __name__ == "__main__":
    asyncio.run(main())
