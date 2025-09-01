"""
Streamlit UI client for the Tax Chatbot (WebSocket backend).

Run:
    streamlit run ui_streamlit.py

Notes:
    - One message per WS connection; the server persists the dossier after reply.
    - Reuse the same dossier id to continue a conversation.
"""

from __future__ import annotations

import os
import uuid
import json
import asyncio
from typing import Any, Dict, List
from pathlib import Path
import time

import streamlit as st
import websockets
from dotenv import load_dotenv

load_dotenv()


DEFAULT_WS_URL = os.getenv("TAX_WS_URL", f"ws://localhost:{os.environ['API_HOST']}/ws")


async def send_ws_message(url: str, message: str, dossier_id: str) -> Dict[str, Any]:
    """Send a message to the tax chatbot WebSocket API.
    
    Args:
        url: WebSocket URL to connect to
        message: User message to send
        dossier_id: Dossier identifier for conversation continuity
        
    Returns:
        Dictionary with response from the server
    """
    async with websockets.connect(url) as ws:
        payload = {"message": message, "dossier_id": dossier_id}
        await ws.send(json.dumps(payload))
        raw = await ws.recv()
        return json.loads(raw)


def run_async(coro):
    """Run an async coroutine from Streamlit context.
    
    Handles cases where an event loop may already be running in the Streamlit
    environment by creating a new loop if needed.
    
    Args:
        coro: Coroutine to execute
        
    Returns:
        Result of the coroutine execution
    """
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
    """Initialize Streamlit session state with default values.
    
    Sets up WebSocket URL, dossier ID, conversation history,
    and selected source titles if not already present.
    """
    if "ws_url" not in st.session_state:
        st.session_state.ws_url = DEFAULT_WS_URL
    if "current_dossier_id" not in st.session_state:
        st.session_state.current_dossier_id = f"dos-{uuid.uuid4().hex[:8]}"
    if "history" not in st.session_state:
        st.session_state.history = []  # list[dict(role, content)]
    if "selected_titles" not in st.session_state:
        st.session_state.selected_titles = []  # list[str]


def reset_conversation(new_dossier: bool = True):
    """Reset the conversation state.
    
    Args:
        new_dossier: If True, generates a new dossier ID. If False,
                    keeps the existing dossier but clears history.
    """
    if new_dossier:
        st.session_state.current_dossier_id = f"dos-{uuid.uuid4().hex[:8]}"
    st.session_state.history = []
    st.session_state.selected_titles = []


def _strip_number_prefix(s: str) -> str:
    """Remove numbered list prefixes from strings.
    
    Args:
        s: String that may have a numbered prefix like "1. "
        
    Returns:
        String with numbered prefix removed
    """
    import re as _re
    return _re.sub(r"^\s*\d+\.\s*", "", s).strip()


def _extract_block(lines: List[str], header: str, stop_headers: List[str]) -> List[str]:
    """Extract a block of text between headers.
    
    Args:
        lines: List of text lines to search
        header: Header text to start extraction from
        stop_headers: List of headers that stop extraction
        
    Returns:
        List of extracted lines with numbered prefixes removed
    """
    try:
        idx = next(i for i, ln in enumerate(lines) if ln.strip().startswith(header))
    except StopIteration:
        return []
    out: List[str] = []
    for ln in lines[idx + 1 :]:
        s = ln.strip()
        if not s:
            break
        if any(s.startswith(h) for h in stop_headers):
            break
        out.append(_strip_number_prefix(s))
    return [x for x in out if x]


def update_selected_from_disk(dossier_id: str, retries: int = 5, delay_s: float = 0.1) -> None:
    """Update selected_titles by reading data/dossiers/{dossier_id}.json.

    Retries briefly because the server persists right after sending.
    """
    dossier_id = (dossier_id or "").strip()
    if not dossier_id:
        return
    path = Path("data/dossiers") / f"{dossier_id}.json"
    for _ in range(max(1, retries)):
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                sel = data.get("selected_ids") or []
                if isinstance(sel, list):
                    # Ensure simple string list
                    st.session_state.selected_titles = [str(x) for x in sel if isinstance(x, (str, int, float))]
                    return
        except Exception:
            pass
        time.sleep(delay_s)


def render_right_sidebar() -> None:
    """Inject a fixed right-side panel that mimics a sidebar.

    Streamlit only has a built-in left sidebar. This function injects a fixed
    panel on the right via CSS so we can show the current selection.
    """
    titles = st.session_state.get("selected_titles", []) or []
    items_html = "".join(f"<li>{t}</li>" for t in titles)
    if not items_html:
        items_html = "<li><em>(Nog geen selectie)</em></li>"

    css = """
    <style>
      /* Right fixed sidebar */
      #rightbar {
        position: fixed;
        /* Nudge below the Streamlit top header */
        top: 3.25rem;
        right: 0;
        width: 360px;
        height: calc(100vh - 3.25rem);
        overflow: auto;
        padding: 0.75rem 1rem 2rem 1rem;
        /* Match Streamlit's sidebar greyish background exactly */
        background: #f0f2f6 !important;
        border-left: 1px solid rgba(49, 51, 63, 0.2);
        z-index: 999;
        box-shadow: -2px 0 6px rgba(0,0,0,0.05);
      }
      #rightbar, #rightbar * { color: inherit; }
      #rightbar h3 { margin: 0.5rem 0 0.75rem; }
      #rightbar ul { margin: 0; padding-left: 1.25rem; }
      #rightbar li { margin: 0.25rem 0; }
      /* Theme-aware text color */
      @media (prefers-color-scheme: dark) {
        #rightbar { background: #0e1117 !important; color: #ffffff; }
      }
      @media (prefers-color-scheme: light) {
        #rightbar { background: #f0f2f6 !important; color: #31333f; }
      }
      @media (max-width: 1000px) {
        div.block-container { padding-right: 1rem; }
        #rightbar { display: none; }
      }
    </style>
    """
    html = f"""
    <div id="rightbar">
      <h3>Geselecteerde titels</h3>
      <ul>{items_html}</ul>
    </div>
    """
    st.markdown(css + html, unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="TESS • Belasting Chatbot", page_icon="💬")
    init_state()

    st.title("TESS • Belasting Chatbot")
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

    # Refresh selection from disk before rendering
    update_selected_from_disk(st.session_state.current_dossier_id)

    # Render chat in main area
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
                # Update selection panel by reading dossier snapshot from disk
                update_selected_from_disk(st.session_state.current_dossier_id)
                with st.chat_message("assistant"):
                    st.markdown(answer)
        except Exception as e:  # network or server failure
            with st.chat_message("assistant"):
                st.error(f"Kon geen verbinding maken met de server: {e}")

    # Inject right-side custom sidebar with current selection (after possible updates)
    render_right_sidebar()


if __name__ == "__main__":
    main()
