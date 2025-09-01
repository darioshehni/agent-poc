
"""Dossier management.

The SessionManager stores Dossier objects in memory and persists them as JSON
snapshots. Tools never touch storage and should not mutate Dossier directly;
they return DossierPatch objects, which are applied under a per‑dossier lock
by the ToolCallHandler. The WebSocket server writes the dossier once per turn
after the reply is sent to the user."""


from typing import Optional
import logging
from pathlib import Path
import json
import uuid

from src.config.models import Dossier
from src.config.config import DOSSIER_BASE_DIR

logger = logging.getLogger(__name__)


def _create_dossier(dossier_id: Optional[str] = None) -> Dossier:
    """Create a new empty dossier.
    
    Args:
        dossier_id: Optional dossier ID. If None, generates a new UUID-based ID.
        
    Returns:
        New empty Dossier instance with the specified or generated ID
    """
    dossier_id = (dossier_id or f"dos-{uuid.uuid4().hex[:8]}")
    dossier = Dossier(dossier_id=dossier_id)
    logger.info(f"Created new dossier with id: {dossier_id}")
    return dossier


def _base_dir() -> Path:
    """Get the base directory for dossier storage.
    
    Returns:
        Path to the dossier storage directory
    """
    return DOSSIER_BASE_DIR


def _dossier_path(dossier_id: str) -> Path:
    """Get the file path for a specific dossier.
    
    Args:
        dossier_id: The dossier identifier
        
    Returns:
        Path to the dossier JSON file
    """
    return _base_dir() / f"{dossier_id}.json"


def save_dossier(dossier: Dossier) -> None:
    """Persist a dossier snapshot to local JSON file.
    
    Creates the storage directory if it doesn't exist. Logs warnings on failure
    but does not raise exceptions. Note: atomicity is not guaranteed.
    
    Args:
        dossier: The dossier instance to save
    """
    try:
        base = _base_dir()
        base.mkdir(parents=True, exist_ok=True)
        payload = dossier.to_dict()
        with _dossier_path(dossier.dossier_id).open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save dossier for id {dossier.dossier_id}: {e}")
    logger.info(f"Saved dossier snapshot for id: {dossier.dossier_id}")


def _load_dossier(dossier_id: str) -> Optional[Dossier]:
    """Load a dossier from JSON file if it exists.
    
    Args:
        dossier_id: The dossier identifier to load
        
    Returns:
        Loaded Dossier instance if file exists and is valid, None otherwise.
        Ensures the loaded dossier has the correct dossier_id set.
    """
    path = _dossier_path(dossier_id)
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


def get_or_create_dossier(dossier_id: str) -> Dossier:
    """Get an existing dossier or create a new one if it doesn't exist.
    
    Args:
        dossier_id: The dossier identifier to load or create
        
    Returns:
        Existing dossier if found in storage, otherwise a new empty dossier
        with the specified ID
    """
    dossier = _load_dossier(dossier_id=dossier_id)
    if dossier:
        return dossier
    return _create_dossier(dossier_id=dossier_id)
