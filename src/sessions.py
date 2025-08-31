
"""Dossier management.

The SessionManager stores Dossier objects in memory and persists them as JSON
snapshots. Tools never touch storage and should not mutate Dossier directly;
they return DossierPatch objects, which are applied under a per‑dossier lock
by the ToolCallHandler. The WebSocket server writes the dossier once per turn
after the reply is sent to the user."""


from typing import Dict, List, Optional
from datetime import datetime
import logging
from pathlib import Path
import json

from src.models import Dossier

logger = logging.getLogger(__name__)


class SessionManager:
    """Manage in-memory Dossiers and simple JSON persistence."""

    def __init__(self) -> None:
        self._dossiers: Dict[str, Dossier] = {}

    def create_dossier(self, dossier_id: str) -> Dossier:
        """Create a new empty dossier with the given id."""
        dossier = Dossier(dossier_id=dossier_id)
        self._dossiers[dossier_id] = dossier
        return dossier

    def get_dossier(self, dossier_id: str) -> Optional[Dossier]:
        """Return the in-memory dossier for this id, if present."""
        return self._dossiers.get(dossier_id)

    def get_or_create_dossier(self, dossier_id: str) -> Dossier:
        """Return an existing dossier or load/create a new one if missing."""
        if dossier_id in self._dossiers:
            return self._dossiers[dossier_id]
        loaded = self.load_dossier(dossier_id)
        if loaded:
            self._dossiers[dossier_id] = loaded
            return loaded
        return self.create_dossier(dossier_id)

    def delete_dossier(self, dossier_id: str) -> bool:
        """Delete an in-memory dossier; returns True if it existed."""
        return self._dossiers.pop(dossier_id, None) is not None

    def list_dossiers(self) -> List[str]:
        """List all in-memory dossier ids."""
        return list(self._dossiers.keys())

    def _base_dir(self) -> Path:
        return Path("data/dossiers")

    def _dossier_path(self, dossier_id: str) -> Path:
        return self._base_dir() / f"{dossier_id}.json"

    def save_dossier(self, dossier: Dossier) -> None:
        """Persist a dossier snapshot to local JSON (atomicity not guaranteed)."""
        try:
            base = self._base_dir()
            base.mkdir(parents=True, exist_ok=True)
            payload = dossier.to_dict()
            with self._dossier_path(dossier.dossier_id).open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save dossier for id {dossier.dossier_id}: {e}")

    def load_dossier(self, dossier_id: str) -> Optional[Dossier]:
        """Load a dossier JSON snapshot if it exists; return None otherwise."""
        path = self._dossier_path(dossier_id)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            dossier = Dossier.from_dict(data)
            if not dossier.dossier_id:
                dossier.dossier_id = dossier_id
            return dossier
        except Exception as e:
            logger.warning(f"Failed to load dossier for id {dossier_id}: {e}")
            return None

    # No compatibility wrappers; use *_dossier APIs only
