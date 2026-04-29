"""Scan Robot Framework libraries to extract keyword metadata."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from robot.libraries import STDLIBS
from robot.libdoc import LibraryDocumentation

logger = logging.getLogger(__name__)

# Libraries to skip during scanning (require external server or user interaction)
SKIP_STDLIBS = {"Remote", "Dialogs", "Easter", "Telnet"}


@dataclass
class KeywordInfo:
    """Metadata for a single Robot Framework keyword."""

    library: str
    name: str
    args: str  # Compact args string, e.g. "path, content=''"
    short_doc: str
    category: str = ""  # Auto-categorized: file, browser, string, etc.

    def to_compact(self) -> str:
        """One-line compact format for AI prompts."""
        return f"{self.library}: {self.name}({self.args}) - {self.short_doc}"

    def to_dict(self) -> dict:
        return {
            "library": self.library,
            "name": self.name,
            "args": self.args,
            "short_doc": self.short_doc,
            "category": self.category,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KeywordInfo":
        return cls(**data)


@dataclass
class LibraryInfo:
    """Metadata for a Robot Framework library."""

    name: str
    version: str = ""
    scope: str = ""
    doc: str = ""
    keywords: list[KeywordInfo] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "scope": self.scope,
            "doc": self.doc,
            "keywords": [kw.to_dict() for kw in self.keywords],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LibraryInfo":
        data["keywords"] = [KeywordInfo.from_dict(k) for k in data.get("keywords", [])]
        return cls(**data)


# Category mapping: library name -> primary category
LIBRARY_CATEGORIES = {
    "BuiltIn": "general",
    "Collections": "collection",
    "DateTime": "datetime",
    "Dialogs": "general",
    "Easter": "general",
    "OperatingSystem": "file",
    "Process": "process",
    "Remote": "general",
    "Screenshot": "image",
    "String": "string",
    "Telnet": "general",
    "XML": "xml",
    "SeleniumLibrary": "browser",
    "Browser": "browser",
    "RPA.Excel.Files": "excel",
    "RPA.Excel.Application": "excel",
    "RPA.PDF": "pdf",
    "RPA.Email.ImapSmtp": "email",
    "RPA.HTTP": "network",
    "RPA.Desktop": "desktop",
    "RPA.Windows": "desktop",
    "RPA.Robocorp.Vault": "security",
    "RPA.Robocorp.WorkItems": "workflow",
    "RequestsLibrary": "network",
    "DatabaseLibrary": "database",
}


def _format_args(kw_doc) -> str:
    """Format keyword arguments into a compact string."""
    if not hasattr(kw_doc, "args") or not kw_doc.args:
        return ""
    arg_strs = []
    for arg in kw_doc.args:
        arg_strs.append(str(arg))
    return ", ".join(arg_strs)


def _categorize_keyword(library_name: str, kw_name: str, kw_doc: str) -> str:
    """Auto-categorize a keyword based on library and name patterns."""
    # Primary category from library
    category = LIBRARY_CATEGORIES.get(library_name, "general")

    # Refine based on keyword name patterns (only for BuiltIn which is too broad)
    if library_name == "BuiltIn":
        name_lower = kw_name.lower()
        if "file" in name_lower or "directory" in name_lower or "path" in name_lower:
            return "file"
        if "log" in name_lower or "comment" in name_lower or "set" in name_lower:
            return "general"
        if "should" in name_lower or "wait" in name_lower:
            return "general"
        if "variable" in name_lower:
            return "general"

    return category


def scan_library(name: str) -> Optional[LibraryInfo]:
    """Scan a single library using LibraryDocumentation API.

    Returns None if the library cannot be imported.
    """
    try:
        lib_doc = LibraryDocumentation(name)
    except Exception as e:
        logger.warning("Failed to scan library '%s': %s", name, e)
        return None

    keywords = []
    for kw in lib_doc.keywords:
        category = _categorize_keyword(name, kw.name, kw.short_doc or "")
        keywords.append(
            KeywordInfo(
                library=name,
                name=kw.name,
                args=_format_args(kw),
                short_doc=(kw.short_doc or "").split("\n")[0][:120],
                category=category,
            )
        )

    return LibraryInfo(
        name=lib_doc.name,
        version=lib_doc.version,
        scope=lib_doc.scope,
        doc=(lib_doc.doc or "")[:200],
        keywords=keywords,
    )


def scan_all_standard_libraries() -> list[LibraryInfo]:
    """Scan all standard libraries (skip problematic ones)."""
    results = []
    for name in sorted(STDLIBS):
        if name in SKIP_STDLIBS:
            logger.debug("Skipping standard library: %s", name)
            continue
        lib = scan_library(name)
        if lib:
            results.append(lib)
            logger.info(
                "Scanned %s: %d keywords", lib.name, len(lib.keywords)
            )
    return results


def scan_libraries(names: list[str]) -> list[LibraryInfo]:
    """Scan a list of library names, skipping failures."""
    results = []
    for name in names:
        lib = scan_library(name)
        if lib:
            results.append(lib)
            logger.info(
                "Scanned %s: %d keywords", lib.name, len(lib.keywords)
            )
    return results
