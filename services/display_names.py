"""Server-side twin of static/display.js for text the browser never formats.

Share previews and page meta tags are read by link scrapers that do not run
JavaScript, so names are given display casing here with the same rules:
"DIABLOS DEL SOL" and "diablos del sol" both read "Diablos del Sol", while
U12, A.C. and short acronyms in mixed-case names keep their capitals.
"""

import re

LOWERCASE_WORDS = {"de", "del", "la", "las", "los", "y", "e", "el", "en"}
_CATEGORY = re.compile(r"^u\d{1,2}$", re.IGNORECASE)
_INITIALISM = re.compile(r"^([a-z]\.)+[a-z]?\.?$", re.IGNORECASE)


def _is_acronym(word):
    return 2 <= len(word) <= 4 and word.isalpha() and word.isupper()


def _capitalize_parts(word):
    # Hyphenated parts are capitalised separately: Ruiz-Esparza.
    return "-".join(part[:1].upper() + part[1:] for part in word.split("-"))


def _display_word(word, index, keep_acronyms):
    if _CATEGORY.match(word) or _INITIALISM.match(word):
        return word.upper()
    if keep_acronyms and _is_acronym(word):
        return word
    lower = word.lower()
    if index > 0 and lower in LOWERCASE_WORDS:
        return lower
    return _capitalize_parts(lower)


def display_name(name):
    text = " ".join(str(name or "").split())
    if not text:
        return ""
    words = text.split(" ")
    typed_in_capitals = text == text.upper()
    keep_acronyms = not typed_in_capitals or len(words) == 1
    return " ".join(_display_word(word, index, keep_acronyms) for index, word in enumerate(words))


def branch_label(branch, category):
    """Unified youth divisions read "Infantiles", as on the site."""
    if str(category or "").lower() in {"u8", "u10", "u12"}:
        return "Infantiles"
    return display_name(branch)


def division_label(branch, category):
    return f"{branch_label(branch, category)} · {display_name(category)}"
