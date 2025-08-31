"""
Streamlit UI client for the Tax Chatbot (WebSocket backend).

Run:
    streamlit run ui_streamlit.py

Environment:
    TAX_WS_URL (default: ws://localhost:8000/ws)

Notes:
    - One message per WS connection; the server persists the dossier after reply.
    - Reuse the same dossier id to continue a conversation.
"""

from __future__ import annotations

import os
import uuid
import json
import asyncio
from typing import Any, Dict

import streamlit as st

try:
    import websockets
except ImportError:  # pragma: no cover
    st.stop()


DEFAULT_WS_URL = os.getenv("TAX_WS_URL", "ws://localhost:8000/ws")


async def send_ws_message(url: str, message: str, dossier_id: str) -> Dict[str, Any]:
    async with websockets.connect(url) as ws:
        payload = {"message": message, "dossier_id": dossier_id}
        await ws.send(json.dumps(payload))
        raw = await ws.recv()
        return json.loads(raw)


def run_async(coro):
    """Run an async coroutine from Streamlit (handles existing loop cases)."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        # If there's already a running loop (rare in Streamlit), create a new one
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def init_state():
    if "ws_url" not in st.session_state:
        st.session_state.ws_url = DEFAULT_WS_URL
    if "current_dossier_id" not in st.session_state:
        st.session_state.current_dossier_id = f"dos-{uuid.uuid4().hex[:8]}"
    if "history" not in st.session_state:
        st.session_state.history = []  # list[dict(role, content)]


def reset_conversation(new_dossier: bool = True):
    if new_dossier:
        st.session_state.current_dossier_id = f"dos-{uuid.uuid4().hex[:8]}"
    st.session_state.history = []


def main():
    st.set_page_config(page_title="TESS • Belasting Chatbot", page_icon="💬")
    init_state()

    st.title("TESS • Nederlandse Belasting Chatbot")
    st.caption("Deze UI praat met de WebSocket server op /ws en bewaart je dossier-id zodat je een gesprek kunt vervolgen.")

    with st.sidebar:
        st.header("Instellingen")
        st.text_input("WebSocket URL", key="ws_url", help="Bijv. ws://localhost:8000/ws")
        st.text("Huidig dossier:")
        st.code(st.session_state.current_dossier_id)
        st.text_input(
            "Dossier ID (invoer)",
            key="dossier_id_input",
            value=st.session_state.current_dossier_id,
            help="Plak een bestaand dossier-id of pas het aan en klik 'Gebruik ID'",
        )
        if st.button("Gebruik ID", use_container_width=True):
            candidate = (st.session_state.get("dossier_id_input") or "").strip()
            if candidate:
                st.session_state.current_dossier_id = candidate
                st.session_state.history = []
                st.rerun()
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Nieuwe sessie", use_container_width=True):
                reset_conversation(new_dossier=True)
                st.rerun()
        with col_b:
            if st.button("Wissen (zelfde dossier)", use_container_width=True):
                reset_conversation(new_dossier=False)
                st.rerun()

        st.markdown("""
        - Server: start met `python src/api/server.py`
        - Run deze UI: `streamlit run ui_streamlit.py`
        """)

    # Show chat history
    for msg in st.session_state.history:
        with st.chat_message("user" if msg["role"] == "user" else "assistant"):
            st.markdown(msg.get("content", ""))

    # Chat input
    user_input = st.chat_input("Typ je bericht en druk op Enter…")
    if user_input:
        # Append user message locally
        st.session_state.history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Send to WS API and display response
        try:
            resp = run_async(send_ws_message(st.session_state.ws_url, user_input, st.session_state.current_dossier_id))
            status = resp.get("status")
            if status != "success":
                err = resp.get("error") or "Onbekende fout"
                with st.chat_message("assistant"):
                    st.error(f"Fout van server: {err}")
            else:
                # Update dossier id (server may return same or new)
                returned_id = resp.get("dossier_id")
                if returned_id:
                    st.session_state.current_dossier_id = returned_id
                answer = resp.get("response", "")
                st.session_state.history.append({"role": "assistant", "content": answer})
                with st.chat_message("assistant"):
                    st.markdown(answer)
        except Exception as e:  # network or server failure
            with st.chat_message("assistant"):
                st.error(f"Kon geen verbinding maken met de server: {e}")


if __name__ == "__main__":
    main()
