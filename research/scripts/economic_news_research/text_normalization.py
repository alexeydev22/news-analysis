import re

URL_PATTERN = re.compile(r"https?://\S+")
SPACE_PATTERN = re.compile(r"\s+")
BOILERPLATE_PATTERNS = (
    re.compile(
        r"\bFintel reports that on "
        r"(?:January|February|March|April|May|June|July|August|September|October|"
        r"November|December)\s+\d{1,2},\s+\d{4},\s*",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bSee our leaderboard of companies with the largest price target upside\.\s*",
        re.IGNORECASE,
    ),
)


def normalize_news_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = URL_PATTERN.sub("", text)
    removed_boilerplate = False
    for pattern in BOILERPLATE_PATTERNS:
        text, replacements = pattern.subn("", text)
        removed_boilerplate = removed_boilerplate or replacements > 0

    text = SPACE_PATTERN.sub(" ", text).strip()
    if removed_boilerplate and text:
        text = text[0].upper() + text[1:]
    return text
