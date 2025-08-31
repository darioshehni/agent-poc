
"""Minimal WebSocket server for the Tax Chatbot.

Per-connection flow:
- Client connects to /ws and sends one JSON message: {"message": str, "dossier_id"?: str}
- Server forwards to TaxChatbot and awaits the response
- Server sends back {"response": str, "dossier_id": str, "status": "success"}
- Server persists the dossier snapshot to data/dossiers/<dossier_id>.json and
  closes the socket"""


import logging
from uuid import uuid4
from typing import Any, Dict

from fastapi import FastAPI, WebSocket
from dotenv import load_dotenv

from src.agent import TaxAssistant

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Tax Chatbot WS API", version="2.0.0")


@app.get("/")
async def root() -> Dict[str, Any]:
    return {"name": "Tax Chatbot WS API", "version": "2.0.0", "endpoint": "/ws"}


@app.websocket("/ws")
async def websocket_chat(ws: WebSocket) -> None:
    await ws.accept()
    try:
        payload = await ws.receive_json()
        message = (payload.get("message") or payload.get("query") or "").strip()
        dossier_id = (payload.get("dossier_id") or "").strip() or f"dos-{uuid4().hex[:8]}"

        if not message:
            await ws.send_json({"status": "error", "error": "message is required"})
            await ws.close()
            return

        # Create a fresh chatbot per connection; session manager loads the dossier if present
        assistant = TaxAssistant(dossier_id=dossier_id)
        response_text = await assistant.process_message(message)

        await ws.send_json({"status": "success", "response": response_text, "dossier_id": dossier_id})
        # Persist the updated dossier snapshot to data/dossiers
        try:
            dossier = assistant.session_manager.get_dossier(dossier_id)
            if dossier:
                assistant.session_manager.save_dossier(dossier)
        except Exception as e:
            logger.warning(f"Failed to save dossier for id {dossier_id}: {e}")
        await ws.close()
    except Exception as e:
        try:
            await ws.send_json({"status": "error", "error": str(e)})
        except Exception:
            pass
        finally:
            await ws.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
