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


class DossierPatch(BaseModel):
    """A typed object describing changes to apply to a Dossier.

    Tools return patches. After the tools are finished the Dossier gets patched.
    """
    add_legislation: list[Legislation] = Field(default_factory=list)
    add_case_law: list[CaseLaw] = Field(default_factory=list)
    select_titles: list[str] = Field(default_factory=list)
    unselect_titles: list[str] = Field(default_factory=list)

    def apply(self, dossier: "Dossier") -> None:
        """Apply this patch to the in-memory dossier (no I/O)."""
        # Legislation: de-dup by title
        if self.add_legislation:
            existing_titles = {leg.title for leg in dossier.legislation}
            for item in self.add_legislation:
                title = item.title.strip()
                if title and title not in existing_titles:
                    dossier.legislation.append(item)
                    existing_titles.add(title)

        # Case law: de-dup by title
        if self.add_case_law:
            existing_titles = {case_law.title for case_law in dossier.case_law}
            for item in self.add_case_law:
                title = item.title.strip()
                if title and title not in existing_titles:
                    dossier.case_law.append(item)
                    existing_titles.add(title)

        # Unselect first (to resolve conflicts predictably)
        if self.unselect_titles:
            keep = [title for title in dossier.selected_ids if title not in set(self.unselect_titles)]
            dossier.selected_ids = keep

        # Select (set semantics)
        if self.select_titles:
            seen = set(dossier.selected_ids)
            for title in self.select_titles:
                if title and title not in seen:
                    dossier.selected_ids.append(title)
                    seen.add(title)


class ToolResult(BaseModel):
    """Lightweight tool outcome: either a patch or an answer string.

    - success: indicates tool execution status
    - data: optional payload (e.g., the final answer string for AnswerTool)
    - error_message: when success is False
    - message: legacy field (unused for now, but kept for compatibility)
    - patch: DossierPatch with changes to apply (retrieval/removal tools)
    """
    success: bool
    data: Any | None = None
    error_message: str = ""
    message: str = ""
    patch: DossierPatch | None = None


class Dossier(BaseModel):
    """Aggregates sources and curated conversation for one user interaction stream.

    The dossier persists the conversation and selected sources across turns to
    support confirmation flows and deterministic answer generation.
    """
    # Identity and timestamps
    dossier_id: str = ""

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
        return self.model_dump(mode="json")

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Dossier":
        return Dossier.model_validate(d)

    def get_selected_legislation(self) -> list[Legislation]:
        """Return selected legislation items."""
        return [l for l in self.legislation if l.title in self.selected_ids]

    def get_selected_case_law(self) -> list[CaseLaw]:
        """Return selected case law items."""
        return [c for c in self.case_law if c.title in self.selected_ids]

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

    def add_conversation_user(self, content: str) -> None:
        if isinstance(content, str) and content.strip():
            self.conversation.append({"role": "user", "content": content})

    def add_conversation_assistant(self, content: str) -> None:
        if isinstance(content, str) and content.strip():
            self.conversation.append({"role": "assistant", "content": content})
