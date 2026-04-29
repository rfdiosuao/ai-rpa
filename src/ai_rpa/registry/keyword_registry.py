"""Keyword registry: indexed catalog of Robot Framework keywords."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from ai_rpa.registry.library_scanner import (
    KeywordInfo,
    LibraryInfo,
    scan_all_standard_libraries,
    scan_libraries,
    LIBRARY_CATEGORIES,
)
from ai_rpa.registry.registry_cache import load_cache, save_cache

logger = logging.getLogger(__name__)

# Fallback keyword stubs for common external libraries (used when not installed)
FALLBACK_KEYWORDS = {
    "SeleniumLibrary": [
        KeywordInfo(library="SeleniumLibrary", name="Open Browser", args="url, browser='firefox'", short_doc="Opens a browser to the given URL", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Close Browser", args="", short_doc="Closes the current browser", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Close All Browsers", args="", short_doc="Closes all open browsers", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Go To", args="url", short_doc="Navigates the browser to the given URL", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Input Text", args="locator, text", short_doc="Types text into text field identified by locator", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Input Password", args="locator, password", short_doc="Types password into text field (masked in logs)", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Click Button", args="locator", short_doc="Clicks button identified by locator", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Click Element", args="locator", short_doc="Clicks element identified by locator", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Click Link", args="locator", short_doc="Clicks link identified by locator", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Get Text", args="locator", short_doc="Returns text value of element identified by locator", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Get Value", args="locator", short_doc="Returns value attribute of element", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Element Should Be Visible", args="locator", short_doc="Verifies element is visible", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Element Should Contain", args="locator, expected", short_doc="Verifies element contains text", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Page Should Contain", args="text", short_doc="Verifies current page contains text", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Page Should Contain Element", args="locator", short_doc="Verifies page contains element", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Wait Until Page Contains", args="text, timeout=None", short_doc="Waits until page contains text", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Wait Until Element Is Visible", args="locator, timeout=None", short_doc="Waits until element is visible", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Capture Page Screenshot", args="filename=selenium-screenshot-{index}.png", short_doc="Takes screenshot of current page", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Get Title", args="", short_doc="Returns the title of current page", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Maximize Browser Window", args="", short_doc="Maximizes current browser window", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Set Selenium Speed", args="value", short_doc="Sets delay between Selenium actions", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Set Selenium Timeout", args="value", short_doc="Sets default Selenium timeout", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Select From List By Value", args="locator, *values", short_doc="Selects options from list by values", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Select From List By Label", args="locator, *labels", short_doc="Selects options from list by labels", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Handle Alert", args="action=ACCEPT, timeout=None", short_doc="Handles browser alert", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Switch Window", args="locator=MAIN", short_doc="Switches between browser windows", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Execute Javascript", args="code", short_doc="Executes JavaScript code", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Add Cookie", args="name, value, path=None", short_doc="Adds cookie to browser", category="browser"),
        KeywordInfo(library="SeleniumLibrary", name="Get Selenium Speed", args="", short_doc="Gets current Selenium speed", category="browser"),
    ],
    "RPA.Excel.Files": [
        KeywordInfo(library="RPA.Excel.Files", name="Open Workbook", args="path", short_doc="Open an existing Excel workbook", category="excel"),
        KeywordInfo(library="RPA.Excel.Files", name="Create Workbook", args="path=None", short_doc="Create a new Excel workbook", category="excel"),
        KeywordInfo(library="RPA.Excel.Files", name="Close Workbook", args="", short_doc="Close the currently open workbook", category="excel"),
        KeywordInfo(library="RPA.Excel.Files", name="Read Worksheet", args="name=None, header=False", short_doc="Read worksheet contents", category="excel"),
        KeywordInfo(library="RPA.Excel.Files", name="Read Cell", args="row, column", short_doc="Read value from a cell", category="excel"),
        KeywordInfo(library="RPA.Excel.Files", name="Write Cell", args="row, column, value", short_doc="Write value to a cell", category="excel"),
        KeywordInfo(library="RPA.Excel.Files", name="Create Worksheet", args="name, content=None", short_doc="Create a new worksheet", category="excel"),
        KeywordInfo(library="RPA.Excel.Files", name="Save Workbook", args="path=None", short_doc="Save the workbook", category="excel"),
        KeywordInfo(library="RPA.Excel.Files", name="List Worksheets", args="", short_doc="List all worksheet names", category="excel"),
        KeywordInfo(library="RPA.Excel.Files", name="Switch Worksheet", args="name", short_doc="Switch to a different worksheet", category="excel"),
        KeywordInfo(library="RPA.Excel.Files", name="Append Rows To Worksheet", args="rows, name=None, header=False", short_doc="Append rows to worksheet", category="excel"),
        KeywordInfo(library="RPA.Excel.Files", name="Remove Worksheet", args="name", short_doc="Remove a worksheet", category="excel"),
        KeywordInfo(library="RPA.Excel.Files", name="Find Empty Row", args="name=None", short_doc="Find the first empty row", category="excel"),
        KeywordInfo(library="RPA.Excel.Files", name="Set Worksheet Value", args="row, column, value, name=None", short_doc="Set value in worksheet cell", category="excel"),
        KeywordInfo(library="RPA.Excel.Files", name="Get Worksheet Value", args="row, column, name=None", short_doc="Get value from worksheet cell", category="excel"),
    ],
    "RPA.Email.ImapSmtp": [
        KeywordInfo(library="RPA.Email.ImapSmtp", name="Send Message", args="sender, recipients, subject, body", short_doc="Send an email message", category="email"),
        KeywordInfo(library="RPA.Email.ImapSmtp", name="Send Message With Attachment", args="sender, recipients, subject, body, attachments", short_doc="Send email with attachments", category="email"),
        KeywordInfo(library="RPA.Email.ImapSmtp", name="List Messages", args="criteria='ALL', source=None", short_doc="List messages matching criteria", category="email"),
        KeywordInfo(library="RPA.Email.ImapSmtp", name="Save Attachment", args="message, target_folder", short_doc="Save email attachment to folder", category="email"),
        KeywordInfo(library="RPA.Email.ImapSmtp", name="Wait For Message", args="criteria='SUBJECT', timeout=300", short_doc="Wait for a message matching criteria", category="email"),
        KeywordInfo(library="RPA.Email.ImapSmtp", name="Delete Message", args="uid", short_doc="Delete a message by UID", category="email"),
        KeywordInfo(library="RPA.Email.ImapSmtp", name="Authorize", args="account, password, smtp_server, imap_server", short_doc="Authorize with email server", category="email"),
    ],
    "RPA.PDF": [
        KeywordInfo(library="RPA.PDF", name="Open PDF", args="source", short_doc="Open a PDF file", category="pdf"),
        KeywordInfo(library="RPA.PDF", name="Close PDF", args="source=None", short_doc="Close a PDF file", category="pdf"),
        KeywordInfo(library="RPA.PDF", name="Get Text From PDF", args="source=None", short_doc="Get all text from PDF", category="pdf"),
        KeywordInfo(library="RPA.PDF", name="Get Number Of Pages", args="source=None", short_doc="Get page count of PDF", category="pdf"),
        KeywordInfo(library="RPA.PDF", name="Extract Pages From PDF", args="source, output_path, pages", short_doc="Extract specific pages from PDF", category="pdf"),
        KeywordInfo(library="RPA.PDF", name="Add Watermark To PDF", args="input_path, output_path, watermark_path", short_doc="Add watermark image to PDF", category="pdf"),
        KeywordInfo(library="RPA.PDF", name="Encrypt PDF", args="source, output_path, user_pwd, owner_pwd", short_doc="Encrypt a PDF file", category="pdf"),
        KeywordInfo(library="RPA.PDF", name="Decrypt PDF", args="source, output_path, password", short_doc="Decrypt a PDF file", category="pdf"),
        KeywordInfo(library="RPA.PDF", name="Get Info", args="source=None", short_doc="Get PDF metadata information", category="pdf"),
    ],
}

# Category -> categories that share keywords (for cross-category lookups)
CATEGORY_GROUPS = {
    "file": {"file", "system", "general"},
    "browser": {"browser", "image"},
    "excel": {"excel"},
    "email": {"email"},
    "pdf": {"pdf"},
    "string": {"string", "general"},
    "datetime": {"datetime", "general"},
    "collection": {"collection", "general"},
    "process": {"process", "file", "general"},
    "xml": {"xml"},
    "system": {"system", "file", "general"},
    "image": {"image"},
    "network": {"network"},
    "database": {"database"},
    "desktop": {"desktop"},
    "general": {"general"},
}


class KeywordRegistry:
    """Indexed catalog of available Robot Framework keywords."""

    def __init__(self):
        self._libraries: dict[str, LibraryInfo] = {}
        self._keywords: list[KeywordInfo] = []
        self._category_index: dict[str, list[KeywordInfo]] = {}
        self._installed_external: set[str] = set()

    def load(self, config, refresh: bool = False) -> None:
        """Load the registry from cache or by scanning."""
        libraries = None
        if not refresh:
            libraries = load_cache(config)

        if libraries is None:
            # Scan standard libraries
            libraries = scan_all_standard_libraries()

            # Scan extra libraries specified in config
            if config.extra_libraries:
                extra = scan_libraries(config.extra_libraries)
                libraries.extend(extra)
                for lib in extra:
                    self._installed_external.add(lib.name)

            # Try to auto-detect common external libraries
            for lib_name in ["SeleniumLibrary", "RPA.Excel.Files", "RPA.PDF", "RPA.Email.ImapSmtp"]:
                if lib_name not in {l.name for l in libraries}:
                    lib = scan_libraries([lib_name])
                    if lib:
                        libraries.extend(lib)
                        self._installed_external.add(lib_name)

            save_cache(config, libraries)

        # Build indices
        for lib in libraries:
            self._libraries[lib.name] = lib
            self._keywords.extend(lib.keywords)
            for kw in lib.keywords:
                self._category_index.setdefault(kw.category, []).append(kw)

        # Add fallback keywords for uninstalled external libraries
        for lib_name, kws in FALLBACK_KEYWORDS.items():
            if lib_name not in self._libraries:
                for kw in kws:
                    self._keywords.append(kw)
                    self._category_index.setdefault(kw.category, []).append(kw)

        logger.info(
            "Registry loaded: %d libraries, %d keywords, %d categories",
            len(self._libraries),
            len(self._keywords),
            len(self._category_index),
        )

    def get_keywords_by_categories(self, categories: list[str]) -> list[KeywordInfo]:
        """Get all keywords matching any of the given categories."""
        result = []
        seen = set()

        # Expand categories via groups
        expanded = set()
        for cat in categories:
            expanded |= CATEGORY_GROUPS.get(cat, {cat})

        for cat in expanded:
            for kw in self._category_index.get(cat, []):
                key = (kw.library, kw.name)
                if key not in seen:
                    seen.add(key)
                    result.append(kw)

        return result

    def get_compact_context(self, categories: list[str], max_keywords: int = 80) -> str:
        """Get compact keyword listing for AI prompt context.

        Returns one-line-per-keyword format, filtered by categories.
        """
        keywords = self.get_keywords_by_categories(categories)

        # Truncate if too many
        if len(keywords) > max_keywords:
            logger.info(
                "Truncating keyword context from %d to %d",
                len(keywords), max_keywords,
            )
            keywords = keywords[:max_keywords]

        lines = [kw.to_compact() for kw in keywords]
        return "\n".join(lines)

    def get_library_names(self) -> list[str]:
        """Get all known library names."""
        return list(self._libraries.keys())

    def is_library_installed(self, name: str) -> bool:
        """Check if an external library is actually installed (not fallback)."""
        return name in self._installed_external or name in self._libraries

    def get_all_categories(self) -> list[str]:
        """Get all keyword categories."""
        return list(self._category_index.keys())
