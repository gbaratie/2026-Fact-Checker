import re
import unicodedata

from unidecode import unidecode


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = unidecode(text).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def candidate_mentioned(text: str, full_name: str) -> bool:
    normalized_text = normalize_text(text)
    normalized_name = normalize_text(full_name)
    if not normalized_name:
        return False
    # Match full name or last name (at least 3 chars)
    parts = normalized_name.split()
    if normalized_name in normalized_text:
        return True
    if len(parts) >= 2:
        last_name = parts[-1]
        if len(last_name) >= 3 and last_name in normalized_text:
            return True
    return False
