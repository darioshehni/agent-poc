from __future__ import annotations

from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class Legislation(BaseModel):
    """Structured representation of a legislation snippet/article."""
    title: str = ""
    content: str = ""


class CaseLaw(BaseModel):
    """Structured representation of a case law entry (jurisprudentie)."""
    title: str = ""
    content: str = ""


class DocumentTitles(BaseModel):
    """Holds titles of documents."""
    titles: list[str] = Field(default_factory=list, description="Titles of sources")


class Dossier(BaseModel):
    """Aggregates sources and curated conversation for one user interaction stream.

    The dossier persists the conversation and selected sources across turns to
    support confirmation flows and deterministic answer generation.
    """
    # Identity and timestamps
    dossier_id: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Collected sources and curated conversation
    legislation: list[Legislation] = Field(default_factory=list)
    case_law: list[CaseLaw] = Field(default_factory=list)
    selected_ids: list[str] = Field(default_factory=list, description="IDs of sources selected for the next action (titles act as IDs)")
    conversation: list[dict[str, str]] = Field(default_factory=list, description="User-visible conversation (role/content)")

    def add_legislation(self, items: list[Legislation]) -> None:
        self.legislation.extend(items)

    def add_case_law(self, items: list[CaseLaw]) -> None:
        self.case_law.extend(items)

    def titles(self) -> list[str]:
        titles: list[str] = []
        titles.extend([l.title for l in self.legislation if (l.title or "").strip()])
        titles.extend([c.title for c in self.case_law if (c.title or "").strip()])
        return [t for t in titles if (t or "").strip()]

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Dossier":
        return Dossier.model_validate(d)

    # --- Selection helpers ---
    def select_by_ids(self, ids: list[str]) -> None:
        self.selected_ids = list(dict.fromkeys(ids))  # de-duplicate, preserve order

    def clear_selection(self) -> None:
        self.selected_ids.clear()
        self.updated_at = datetime.now()

    def _texts_from_legislation(self, items: list[Legislation]) -> list[str]:
        return [getattr(x, 'content', str(x)) for x in items]

    def _texts_from_case_law(self, items: list[CaseLaw]) -> list[str]:
        return [getattr(x, 'content', str(x)) for x in items]

    def selected_texts(self) -> dict[str, list[str]]:
        if not self.selected_ids:
            return {"legislation": [], "case_law": []}
        # Titles function as identifiers for selection
        leg_sel = [l for l in self.legislation if l.title in self.selected_ids]
        cas_sel = [c for c in self.case_law if c.title in self.selected_ids]
        return {
            "legislation": self._texts_from_legislation(leg_sel),
            "case_law": self._texts_from_case_law(cas_sel),
        }

    def all_texts(self) -> dict[str, list[str]]:
        return {
            "legislation": self._texts_from_legislation(self.legislation),
            "case_law": self._texts_from_case_law(self.case_law),
        }

    def selected_titles(self) -> list[str]:
        """Return titles for currently selected sources."""
        titles: list[str] = []
        titles.extend([l.title for l in self.legislation if l.title in self.selected_ids and l.title])
        titles.extend([c.title for c in self.case_law if c.title in self.selected_ids and c.title])
        return titles

    def unselected_titles(self) -> list[str]:
        """Return titles for collected but currently unselected sources."""
        titles: list[str] = []
        titles.extend([l.title for l in self.legislation if l.title not in self.selected_ids and l.title])
        titles.extend([c.title for c in self.case_law if c.title not in self.selected_ids and c.title])
        return titles

    # --- Conversation helpers (user-visible) ---
    def add_conversation_user(self, content: str) -> None:
        if isinstance(content, str) and content.strip():
            self.conversation.append({"role": "user", "content": content})
            self.updated_at = datetime.now()

    def add_conversation_assistant(self, content: str) -> None:
        if isinstance(content, str) and content.strip():
            self.conversation.append({"role": "assistant", "content": content})
            self.updated_at = datetime.now()


class RemovalDecision(BaseModel):
    """Structured result for removing sources from a dossier.

    Tools that help map user instructions (e.g., "remove article 13") to
    concrete dossier entries should return this object so the agent can update
    state deterministically by ID.
    """
    remove_ids: list[str] = Field(default_factory=list)
    reasoning: Optional[str] = None
