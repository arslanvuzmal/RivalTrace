"""Demo mode stand-in for the model call.

With DEMO_MODE=true, generate_strategic_insights() returns this instead of calling Claude: the changes
found in the sanitized delta, grouped by simple keyword rules, and fixed guidance per group. It says
so in the summary. Nothing here is a model's judgement; it lets the pipeline (diff, sanitising,
briefing history, portal, email rendering) run with no API key.
"""

import re

from app.schemas.insights import CompetitorInsight

_CATEGORIES = [
    ("Pricing", re.compile(r"price|pricing|plan|£|\$|€|discount|fee", re.I)),
    ("Product", re.compile(r"product|service|feature|treatment|offer", re.I)),
    ("Marketing", re.compile(r"headline|tagline|title|banner|hero|campaign", re.I)),
]

_MEANING = {
    "Pricing": "Their prices or plans moved; compare your own position on the same items.",
    "Product": "They added or removed something they sell; check whether customers will compare it with yours.",
    "Marketing": "They changed how they describe themselves; note the message they now lead with.",
    "Other": "A change outside pricing, products and messaging.",
}

_ACTION = {
    "Pricing": ("Action", "Review your prices for the items that changed."),
    "Product": ("Monitor", "Watch whether the new or removed offer lasts beyond this week."),
    "Marketing": ("Monitor", "Keep the old and new wording side by side for next week's comparison."),
    "Other": ("Monitor", "No action unless it repeats."),
}


def _path(raw: str) -> str:
    """"root['plans'][0]['price']" -> "plans 1 price" (1-based for people)."""
    raw = raw.replace("root", "")
    raw = re.sub(r"\['([^']+)'\]", r" \1", raw)
    raw = re.sub(r"\[(\d+)\]", lambda m: f" {int(m.group(1)) + 1}", raw)
    return raw.replace("_", " ").strip()


def _changes(sanitized_delta: str) -> list[str]:
    """Pair the sanitised delta's lines back up into one sentence per change.

    Lines look like "modified_items -> root['headline'] -> new_value: ...", with the old value on
    its own line, and an added list item may be split into one line per field.
    """
    groups: dict[tuple[str, str], dict[str, str]] = {}
    for line in sanitized_delta.splitlines():
        if ": " not in line or "TRUNCATED" in line:
            continue
        left, value = line.split(": ", 1)
        parts = left.split(" -> ")
        kind = parts[0].replace("_items", "")
        path = _path(parts[1]) if len(parts) > 1 else ""
        field = parts[2] if len(parts) > 2 else ""
        groups.setdefault((kind, path), {})[field] = value

    out = []
    for (kind, path), fields in groups.items():
        if kind == "modified" and "new_value" in fields:
            out.append(f"{path}: {fields.get('old_value', '?')} → {fields['new_value']}")
        elif kind in ("added", "removed"):
            item = ", ".join(v for v in fields.values())
            where = re.sub(r" \d+$", "", path)
            out.append(f"{'Added to' if kind == 'added' else 'Removed from'} {where}: {item}")
        else:
            out.append(f"{kind} {path}: " + ", ".join(fields.values()))
    return out


def demo_insight(competitor_name: str, sanitized_delta: str) -> CompetitorInsight:
    lines = _changes(sanitized_delta)
    changed = []
    seen: list[str] = []
    for line in lines[:8]:
        category = next((name for name, pattern in _CATEGORIES if pattern.search(line)), "Other")
        if category not in seen:
            seen.append(category)
        changed.append({"category": category, "description": line})

    threat = "MEDIUM" if ("Pricing" in seen or "Product" in seen) else "LOW"
    groups = ", ".join(seen).lower() if seen else "nothing"
    return CompetitorInsight(
        executive_summary=(
            f"Demo mode (rules, no model): {len(lines)} change(s) on {competitor_name}'s site, in {groups}."
        ),
        threat_level=threat,
        what_changed=changed,
        what_it_means=[
            {"category": "Strategy" if c != "Pricing" else "Market Position", "description": _MEANING[c]}
            for c in seen
        ],
        what_to_do=[{"category": _ACTION[c][0], "description": _ACTION[c][1]} for c in seen],
    )
