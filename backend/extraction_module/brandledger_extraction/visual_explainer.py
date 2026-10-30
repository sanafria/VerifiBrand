"""Turns the extraction.visual block into a plain-language summary for the agent."""
from typing import Any, Dict, Optional

_LABELS = {"visual_colour": "brand colour", "visual_clearspace": "logo clear space",
           "visual_typography": "typography", "visual_layout": "layout hierarchy"}


def _g(obj: Any, key: str, default: Any = None) -> Any:
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def explain_visual(visual: Optional[Dict[str, Any]]) -> str:
    if not visual:
        return "No visual check result is available, so nothing can be said about how this creative looks."
    if not _g(visual, "processed", False):
        return ("The visual checks did not run because the file could not be opened. "
                "This is not a pass. A person needs to review it.")
    ran = list(_g(visual, "checks_run", []) or [])
    findings = list(_g(visual, "findings", []) or [])
    skipped = list(_g(visual, "skipped", []) or [])
    errors = list(_g(visual, "errors", []) or [])
    out = []
    out.append("Checked: " + (", ".join(_LABELS.get(c, c) for c in ran) if ran else "nothing") + ".")
    problems = [f for f in findings if _g(f, "status") == "fail"]
    reviews = [f for f in findings if _g(f, "status") == "needs_review"]
    for f in problems:
        out.append(f"Problem ({_LABELS.get(_g(f, 'category'), _g(f, 'category'))}): {_g(f, 'matched_text', '')}. "
                   f"{_g(f, 'explanation', '')} Fix: {_g(f, 'suggested_fix', 'see the rule')}")
    for f in reviews:
        out.append(f"A person must confirm ({_LABELS.get(_g(f, 'category'), _g(f, 'category'))}): "
                   f"{_g(f, 'matched_text', '')}. {_g(f, 'explanation', '')}")
    if skipped:
        out.append("Not checked: " + "; ".join(skipped) + ".")
    if errors:
        out.append("Could not complete: " + "; ".join(errors) + ". These checks did not pass.")
    if not problems and not reviews and not errors and ran:
        out.append("No issues were found in the checks that ran. This does not mean the creative is fully compliant.")
    return "\n".join(out)
