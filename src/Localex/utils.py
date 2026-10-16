"""
Utility functions for language detection, text chunking, paragraph preservation, and formatting.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextBlockFormat, QTextCursor, QTextOption

if TYPE_CHECKING:
    from PySide6.QtWidgets import QLabel, QTextEdit

import unicodedata

# Unicode ranges for Arabic scripts
ARABIC_BLOCK_RANGES = (
    (0x0600, 0x06FF),  # Arabic
    (0x0750, 0x077F),  # Arabic Supplement
    (0x08A0, 0x08FF),  # Arabic Extended-A
    (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
    (0x10E60, 0x10E7F),  # Rumi Numeral Symbols
    (0x1EC70, 0x1ECBF),  # Indic Siyaq Numbers
    (0x1ED00, 0x1ED4F),  # Ottoman Siyaq Numbers
    (0x1EE00, 0x1EEFF),  # Arabic Mathematical Alphabetic Symbols
)

URL_RE = re.compile(r"https?://[^\s<>'\"`]+|www\.[^\s<>'\"`]+")
CODE_BLOCK_RE = re.compile(r"```[\w-]*\n[\s\S]*?```|`[^`\r\n]+`")
MD_URL_RE = re.compile(r"\]\([^\)\s]+\)")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
HTML_TAG_RE = re.compile(r"<[^>]+>")
HTML_ENTITY_RE = re.compile(r"&[a-zA-Z0-9#]+;")
CITATION_RE = re.compile(r"\[\d+\]")
MD_SYMBOLS_RE = re.compile(r"[*_~#>`|]")


def is_arabic_char(c: str) -> bool:
    """Checks if a single character belongs to any Arabic Unicode block or has Arabic BiDi category."""
    if not c:
        return False
    cp = ord(c)
    for start, end in ARABIC_BLOCK_RANGES:
        if start <= cp <= end:
            return True
    return unicodedata.bidirectional(c) in ("AL", "R")


def clean_text_for_detection(text: str) -> str:
    """
    Removes HTML tags, entities, URLs, code blocks, markdown links, citations,
    and markup symbols for accurate, unbiased language and direction detection.
    """
    if not text:
        return ""
    t = CODE_BLOCK_RE.sub(" ", text)
    t = MD_URL_RE.sub("]", t)
    t = URL_RE.sub(" ", t)
    t = EMAIL_RE.sub(" ", t)
    t = HTML_TAG_RE.sub(" ", t)
    t = HTML_ENTITY_RE.sub(" ", t)
    t = CITATION_RE.sub(" ", t)
    t = MD_SYMBOLS_RE.sub(" ", t)
    return t


def is_arabic_script(text: str) -> bool:
    """Checks if text contains any Arabic characters."""
    if not text:
        return False
    clean = clean_text_for_detection(text)
    return any(is_arabic_char(c) for c in clean)


def get_text_direction(text: str) -> str:
    """
    Detect the natural writing direction reliably for plain, rich, or mixed text.

    Rules:
    - Strips HTML tags, markdown, URLs, code blocks, and citations first.
    - If Arabic characters are present in a meaningful amount (>= 20% of letters, or >= latin count),
      it indicates Arabic sentence structure with embedded technical/Latin terms => RTL.
    - If no Arabic characters exist and Latin characters exist => LTR.
    - If neither (pure numbers, punctuation) => inspect strong directional characters, fallback to LTR.
    """
    if not text or not text.strip():
        return "ltr"

    clean = clean_text_for_detection(text).strip()
    if not clean:
        return "ltr"

    arabic_chars = sum(1 for c in clean if is_arabic_char(c))
    latin_chars = sum(1 for c in clean if unicodedata.bidirectional(c) == "L")

    # If Arabic letters exist
    if arabic_chars > 0:
        total_letters = arabic_chars + latin_chars
        # Arabic technical texts frequently begin with or embed Latin words (e.g. Python, Docker, API, Windows)
        if arabic_chars >= latin_chars or (arabic_chars / max(1, total_letters)) >= 0.20 or arabic_chars >= 4:
            return "rtl"

    if latin_chars > 0:
        return "ltr"

    # Fallback to inspecting strong directional characters (e.g. Hebrew or other scripts)
    for char in clean:
        bidi = unicodedata.bidirectional(char)
        if bidi in ("R", "AL"):
            return "rtl"
        if bidi == "L":
            return "ltr"

    return "rtl" if is_arabic_script(clean) else "ltr"


def detect_language(text: str) -> str:
    """
    Detects whether the given text is predominantly Arabic ('ar') or English ('en').
    Prioritizes Arabic whenever Arabic letters are present in user input.
    """
    if not text or not text.strip():
        return "en"

    clean = clean_text_for_detection(text).strip()
    if not clean:
        return "en"

    arabic_chars = sum(1 for c in clean if is_arabic_char(c))
    latin_chars = sum(1 for c in clean if unicodedata.bidirectional(c) == "L")

    # If Arabic letters exist, technical Arabic text often embeds English terms (Laravel, PHP, etc.)
    if arabic_chars > 0:
        if arabic_chars >= latin_chars or (arabic_chars / max(1, arabic_chars + latin_chars)) >= 0.15:
            return "ar"

    if latin_chars > 0:
        return "en"

    return "ar" if get_text_direction(clean) == "rtl" else "en"



def set_text_edit_content(
    text_edit: QTextEdit,
    text: str,
    is_arabic: Optional[bool] = None,
) -> None:
    """Set text with reliable RTL/LTR direction and alignment, preventing rich-text corruption."""
    # Ensure plain text mode to avoid pasting HTML or foreign markdown direction tags
    text_edit.setAcceptRichText(False)

    if is_arabic is None:
        is_arabic = (
            get_text_direction(text) == "rtl"
            or is_arabic_script(text)
        )

    direction = (
        Qt.RightToLeft if is_arabic else Qt.LeftToRight
    )
    alignment = (
        (Qt.AlignRight | Qt.AlignAbsolute) if is_arabic else (Qt.AlignLeft | Qt.AlignAbsolute)
    )

    # Apply direction before setting the content.
    text_edit.setLayoutDirection(direction)
    if text_edit.viewport():
        text_edit.viewport().setLayoutDirection(direction)

    # Set the default direction and alignment for the document.
    doc = text_edit.document()
    option = doc.defaultTextOption()
    option.setTextDirection(direction)
    option.setAlignment(alignment)
    doc.setDefaultTextOption(option)

    # Set content as pure plain text after configuring document defaults.
    text_edit.setPlainText(text)

    # Explicitly format every paragraph.
    cursor = QTextCursor(doc)
    cursor.beginEditBlock()

    block = doc.begin()
    while block.isValid():
        block_text = block.text()

        if block_text.strip():
            b_clean = clean_text_for_detection(block_text)
            rtl = (
                get_text_direction(b_clean) == "rtl"
                or is_arabic_script(b_clean)
            )
            # If the document is Arabic and this line contains no letters (e.g. bullets, numbers, dashes), follow document direction
            if not rtl and is_arabic and not any(c.isalpha() for c in block_text):
                rtl = True
        else:
            rtl = is_arabic

        block_format = block.blockFormat()
        block_format.setLayoutDirection(
            Qt.RightToLeft if rtl else Qt.LeftToRight
        )
        block_format.setAlignment(
            (Qt.AlignRight | Qt.AlignAbsolute) if rtl else (Qt.AlignLeft | Qt.AlignAbsolute)
        )

        cursor.setPosition(block.position())
        cursor.setBlockFormat(block_format)

        block = block.next()

    cursor.endEditBlock()

    # Keep the cursor at the beginning and explicitly set widget alignment
    cursor.movePosition(QTextCursor.Start)
    text_edit.setTextCursor(cursor)
    text_edit.setAlignment(alignment)


def update_text_edit_direction(text_edit: QTextEdit, is_arabic: bool) -> None:
    """
    Dynamically updates layout direction and alignment while user is actively typing.
    Preserves exact cursor position.
    """
    text_edit.setAcceptRichText(False)
    direction = Qt.RightToLeft if is_arabic else Qt.LeftToRight
    alignment = (Qt.AlignRight | Qt.AlignAbsolute) if is_arabic else (Qt.AlignLeft | Qt.AlignAbsolute)

    saved_pos = text_edit.textCursor().position()
    text_edit.setLayoutDirection(direction)
    if text_edit.viewport():
        text_edit.viewport().setLayoutDirection(direction)

    doc = text_edit.document()
    opt = doc.defaultTextOption()
    opt.setTextDirection(direction)
    opt.setAlignment(alignment)
    doc.setDefaultTextOption(opt)

    cursor = QTextCursor(doc)
    cursor.beginEditBlock()
    block = doc.begin()
    while block.isValid():
        cursor.setPosition(block.position())
        block_text = block.text()
        if block_text.strip():
            b_clean = clean_text_for_detection(block_text)
            b_ar = (get_text_direction(b_clean) == "rtl") or is_arabic_script(b_clean)
            if not b_ar and is_arabic and not any(c.isalpha() for c in block_text):
                b_ar = True
            b_dir = Qt.RightToLeft if b_ar else Qt.LeftToRight
            b_align = (Qt.AlignRight | Qt.AlignAbsolute) if b_ar else (Qt.AlignLeft | Qt.AlignAbsolute)
        else:
            b_dir = direction
            b_align = alignment
        bf = block.blockFormat()
        bf.setLayoutDirection(b_dir)
        bf.setAlignment(b_align)
        cursor.setBlockFormat(bf)
        block = block.next()
    cursor.endEditBlock()

    cur = text_edit.textCursor()
    cur.setPosition(min(saved_pos, max(0, doc.characterCount() - 1)))
    text_edit.setTextCursor(cur)
    text_edit.setAlignment(alignment)


def set_label_direction(label: QLabel, text: str, is_arabic: Optional[bool] = None) -> None:
    """Sets text on a QLabel with proper RTL/LTR layout direction and alignment."""
    if is_arabic is None:
        is_arabic = (get_text_direction(text) == "rtl") or is_arabic_script(text)
    direction = Qt.RightToLeft if is_arabic else Qt.LeftToRight
    alignment = (Qt.AlignRight | Qt.AlignAbsolute | Qt.AlignVCenter) if is_arabic else (Qt.AlignLeft | Qt.AlignAbsolute | Qt.AlignVCenter)
    label.setText(text)
    label.setLayoutDirection(direction)
    label.setAlignment(alignment)


def split_sentences(text: str, max_chars: int = 400) -> List[str]:
    """
    Splits a single paragraph into sentence chunks of at most max_chars when possible.
    Preserves punctuation boundaries (. ! ? ؟ ؛).
    """
    text = text.strip()
    if not text or len(text) <= max_chars:
        return [text] if text else []

    # Delimiters for Arabic and English sentences
    delimiters = r"([.?!؟;؛\n]+)"
    tokens = re.split(delimiters, text)

    chunks: List[str] = []
    current_chunk = ""

    def _add_piece(piece_text: str) -> None:
        nonlocal current_chunk
        p = piece_text.strip()
        if not p:
            return
        if len(p) > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            words = p.split(" ")
            sub = ""
            for w in words:
                if not w:
                    continue
                if len(sub) + len(w) + 1 <= max_chars:
                    sub = f"{sub} {w}" if sub else w
                else:
                    if sub:
                        chunks.append(sub.strip())
                    sub = w
            if sub:
                chunks.append(sub.strip())
        elif current_chunk and len(current_chunk) + len(p) + 1 <= max_chars:
            current_chunk = f"{current_chunk} {p}"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = p

    for i in range(0, len(tokens) - 1, 2):
        sentence = tokens[i]
        delim = tokens[i + 1] if i + 1 < len(tokens) else ""
        piece = (sentence + delim).strip()
        _add_piece(piece)

    # Handle any trailing token
    if len(tokens) % 2 != 0 and tokens[-1].strip():
        _add_piece(tokens[-1].strip())

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks if chunks else [text]


def chunk_text_by_paragraphs(text: str, max_chunk_chars: int = 500) -> List[Tuple[str, str]]:
    """
    Deconstructs multi-paragraph text into a list of (chunk_text, separator_after)
    so that paragraphs and linebreaks can be reconstructed exactly after translation.
    """
    if not text:
        return []

    # Split lines while tracking line endings
    lines = text.splitlines(keepends=True)
    result: List[Tuple[str, str]] = []

    for line in lines:
        newline = ""
        content = line
        if content.endswith("\r\n"):
            newline = "\r\n"
            content = content[:-2]
        elif content.endswith("\n"):
            newline = "\n"
            content = content[:-1]
        elif content.endswith("\r"):
            newline = "\r"
            content = content[:-1]

        if not content.strip():
            # Blank line: keep as empty chunk with its newline
            result.append(("", newline))
            continue

        # Split content if too long
        sub_chunks = split_sentences(content, max_chars=max_chunk_chars)
        for i, sc in enumerate(sub_chunks):
            sep = newline if i == len(sub_chunks) - 1 else " "
            result.append((sc, sep))

    return result


def format_bytes(bytes_count: int | float) -> str:
    """Formats bytes into human-readable representation."""
    b = float(bytes_count)
    if b < 1024:
        return f"{int(b)} B"
    kb = b / 1024
    if kb < 1024:
        return f"{kb:.1f} KB"
    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.1f} MB"
    gb = mb / 1024
    return f"{gb:.2f} GB"


def format_speed(bytes_per_sec: float) -> str:
    """Formats speed in bytes/sec to human readable format."""
    return f"{format_bytes(bytes_per_sec)}/s"


def format_eta(seconds: float) -> str:
    """Formats estimated seconds into min:sec."""
    s = int(seconds)
    if s < 0 or s > 86400:
        return "--:--"
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m {s:02d}s"


def mask_special_content(text: str) -> Tuple[str, List[dict]]:
    """
    Extracts code blocks, inline code, markdown links, raw URLs, and emails.
    Replaces them with standard citation tokens [0], [1], etc., which are preserved
    by NLLB without translation.
    """
    masked_items: List[dict] = []

    def _add_item(item_type: str, raw_text: str, label: str = "", url: str = "") -> str:
        idx = len(masked_items)
        masked_items.append({
            "index": str(idx),
            "type": item_type,
            "raw_text": raw_text,
            "label": label,
            "url": url,
        })
        return f"[{idx}]"

    # 1. Fenced code blocks ```...```
    def _repl_code_block(m: re.Match) -> str:
        return _add_item("code_block", m.group(0))

    text = re.sub(r"```[\w-]*\n[\s\S]*?```", _repl_code_block, text)

    # 2. Inline code `...`
    def _repl_inline_code(m: re.Match) -> str:
        return _add_item("inline_code", m.group(0))

    text = re.sub(r"`[^`\r\n]+`", _repl_inline_code, text)

    # 3. Markdown links [label](url)
    def _repl_md_link(m: re.Match) -> str:
        return _add_item("md_link", m.group(0), label=m.group(1), url=m.group(2))

    text = re.sub(r"\[([^\]\r\n]+)\]\(([^\)\s]+)\)", _repl_md_link, text)

    # 4. Standalone URLs
    def _repl_url(m: re.Match) -> str:
        return _add_item("raw_url", m.group(0), url=m.group(0))

    text = re.sub(r"https?://[^\s<>'\"`]+", _repl_url, text)

    # 5. Emails
    def _repl_email(m: re.Match) -> str:
        return _add_item("email", m.group(0))

    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", _repl_email, text)

    return text, masked_items


def restore_special_content(
    text: str,
    masked_items: List[dict],
    translated_labels: Optional[dict] = None,
) -> str:
    """
    Restores masked placeholders [0], [1], etc. with their original or translated values.
    """
    if not masked_items:
        return text

    translated_labels = translated_labels or {}

    for item in masked_items:
        idx = item["index"]
        item_type = item["type"]

        if item_type == "md_link":
            tr_label = translated_labels.get(idx, item["label"])
            replacement = f"[{tr_label}]({item['url']})"
        else:
            replacement = item["raw_text"]

        # Resilient match for [idx], [idx, or idx]
        pattern = re.compile(rf"(?:\[\s*{re.escape(idx)}\s*\]|\[\s*{re.escape(idx)}\b|\b{re.escape(idx)}\s*\])")
        text = pattern.sub(lambda _: replacement, text)

    return text

