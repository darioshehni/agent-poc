"""
Session and dossier management (no QuerySession wrapper).

The SessionManager manages Dossier objects directly in memory and persists them
as JSON. Tools update the in-memory Dossier; the server persists once per turn.
"""

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
        dossier = Dossier(dossier_id=dossier_id)
        self._dossiers[dossier_id] = dossier
        return dossier

    def get_dossier(self, dossier_id: str) -> Optional[Dossier]:
        return self._dossiers.get(dossier_id)

    def get_or_create_dossier(self, dossier_id: str) -> Dossier:
        if dossier_id in self._dossiers:
            return self._dossiers[dossier_id]
        loaded = self.load_dossier(dossier_id)
        if loaded:
            self._dossiers[dossier_id] = loaded
            return loaded
        return self.create_dossier(dossier_id)

    def delete_dossier(self, dossier_id: str) -> bool:
        return self._dossiers.pop(dossier_id, None) is not None

    def list_dossiers(self) -> List[str]:
        return list(self._dossiers.keys())

    def cleanup_old_sessions(self, hours_old: int = 24) -> int:
        cutoff = datetime.now().timestamp() - (hours_old * 3600)
        to_remove = [sid for sid, dos in self._dossiers.items() if dos.updated_at.timestamp() < cutoff]
        for sid in to_remove:
            del self._dossiers[sid]
        return len(to_remove)

    def _base_dir(self) -> Path:
        return Path("data/dossiers")

    def _dossier_path(self, dossier_id: str) -> Path:
        return self._base_dir() / f"{dossier_id}.json"

    def save_dossier(self, dossier: Dossier) -> None:
        """Persist a dossier snapshot to local JSON."""
        try:
            base = self._base_dir()
            base.mkdir(parents=True, exist_ok=True)
            payload = dossier.to_dict()
            with self._dossier_path(dossier.dossier_id).open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save dossier for id {dossier.dossier_id}: {e}")

    def load_dossier(self, dossier_id: str) -> Optional[Dossier]:
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
