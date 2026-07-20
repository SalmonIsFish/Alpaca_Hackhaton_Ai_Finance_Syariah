"""Read local Obsidian policy notes for explanations; never overrides gates."""

from pathlib import Path

from config import load_settings


def find_policy_context(query: str, *, limit: int = 3) -> list[dict]:
    settings = load_settings()
    if not settings.shariah_wiki_path:
        return []
    root = Path(settings.shariah_wiki_path)
    if not root.exists():
        return []

    terms = {term.lower() for term in query.split() if len(term) > 3}
    matches: list[tuple[int, dict]] = []
    for path in root.rglob("*.md"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lower = text.lower()
        score = sum(lower.count(term) for term in terms)
        if score:
            excerpt = " ".join(text.strip().split())[:600]
            matches.append((score, {"file": str(path), "excerpt": excerpt}))
    matches.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in matches[:limit]]
