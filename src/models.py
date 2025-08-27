from __future__ import annotations

from typing import List, Optional, Any, Dict
import uuid
from pydantic import BaseModel, Field


def _gen_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class Legislation(BaseModel):
    """Structured representation of a legislation snippet/article.

    Fields capture identifiers and minimal metadata plus the raw `content`
    text used for downstream answer generation and display.
    """
    id: str = Field(default_factory=lambda: _gen_id("LEG"))
    title: str = ""
    law: Optional[str] = None
    article: Optional[str] = None
    content: str = ""
    citation: Optional[str] = None
    url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Legislation":
        return Legislation.model_validate(d)


class CaseLaw(BaseModel):
    """Structured representation of a case law entry (jurisprudentie)."""
    id: str = Field(default_factory=lambda: _gen_id("CAS"))
    title: str = ""
    court: Optional[str] = None
    ecli: Optional[str] = None
    content: str = ""
    date: Optional[str] = None
    url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "CaseLaw":
        return CaseLaw.model_validate(d)


class Dossier(BaseModel):
    """Aggregates sources collected during a session.

    The dossier travels with the session to support confirmation flows and
    deterministic answer generation based on known sources.
    """
    legislation: List[Legislation] = Field(default_factory=list)
    case_law: List[CaseLaw] = Field(default_factory=list)
    selected_ids: List[str] = Field(default_factory=list, description="IDs of sources selected for the next action")

    def add_legislation(self, items: List[Legislation]) -> None:
        self.legislation.extend(items)

    def add_case_law(self, items: List[CaseLaw]) -> None:
        self.case_law.extend(items)

    def titles(self) -> List[str]:
        titles: List[str] = []
        titles.extend([l.title or (l.law or "") for l in self.legislation])
        titles.extend([c.title or (c.ecli or "") for c in self.case_law])
        return [t for t in titles if t]

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Dossier":
        return Dossier.model_validate(d)

    # --- Selection helpers ---
    def select_by_ids(self, ids: List[str]) -> None:
        self.selected_ids = list(dict.fromkeys(ids))  # de-duplicate, preserve order

    def clear_selection(self) -> None:
        self.selected_ids.clear()

    def _texts_from_legislation(self, items: List[Legislation]) -> List[str]:
        return [getattr(x, 'content', str(x)) for x in items]

    def _texts_from_case_law(self, items: List[CaseLaw]) -> List[str]:
        return [getattr(x, 'content', str(x)) for x in items]

    def selected_texts(self) -> Dict[str, List[str]]:
        if not self.selected_ids:
            return {"legislation": [], "case_law": []}
        leg_sel = [l for l in self.legislation if l.id in self.selected_ids]
        cas_sel = [c for c in self.case_law if c.id in self.selected_ids]
        return {
            "legislation": self._texts_from_legislation(leg_sel),
            "case_law": self._texts_from_case_law(cas_sel),
        }

    def all_texts(self) -> Dict[str, List[str]]:
        return {
            "legislation": self._texts_from_legislation(self.legislation),
            "case_law": self._texts_from_case_law(self.case_law),
        }

    def selected_titles(self) -> List[str]:
        """Return titles for currently selected sources."""
        titles: List[str] = []
        titles.extend([l.title for l in self.legislation if l.id in self.selected_ids and l.title])
        titles.extend([c.title for c in self.case_law if c.id in self.selected_ids and c.title])
        return titles

    def unselected_titles(self) -> List[str]:
        """Return titles for collected but currently unselected sources."""
        titles: List[str] = []
        titles.extend([l.title for l in self.legislation if l.id not in self.selected_ids and l.title])
        titles.extend([c.title for c in self.case_law if c.id not in self.selected_ids and c.title])
        return titles


class RemovalDecision(BaseModel):
    """Structured result for removing sources from a dossier.

    Tools that help map user instructions (e.g., "remove article 13") to
    concrete dossier entries should return this object so the agent can update
    state deterministically by ID.
    """
    remove_ids: List[str] = Field(default_factory=list)
    reasoning: Optional[str] = None
