import re
import unicodedata

from unidecode import unidecode


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = unidecode(text).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _contains_phrase(text: str, phrase: str) -> bool:
    if not phrase:
        return False
    pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"
    return re.search(pattern, text) is not None


def candidate_mentioned(text: str, full_name: str) -> bool:
    normalized_text = normalize_text(text)
    normalized_name = normalize_text(full_name)
    if not normalized_name:
        return False

    if _contains_phrase(normalized_text, normalized_name):
        return True

    parts = normalized_name.split()
    if len(parts) < 2:
        return False

    # Prefer multi-word last names ("le pen") over a too-short token ("pen")
    last_name = parts[-1]
    if len(parts) >= 3 and len(last_name) <= 3:
        compound = " ".join(parts[-2:])
        if _contains_phrase(normalized_text, compound):
            return True

    if len(last_name) >= 4 and _contains_phrase(normalized_text, last_name):
        return True

    return False
