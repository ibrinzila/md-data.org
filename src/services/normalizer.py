import re


def normalize_query(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())

