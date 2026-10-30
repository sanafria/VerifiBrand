"""Visual-check explanation for the agent.

explain_creative_visuals(client, file_bytes, filename) uploads a creative to
POST /api/scans/upload, reads extraction.visual, and returns plain text.
Rules: never judge an image that was not processed; checks_run is the source of
truth; skipped/errored checks are never reported as passes; needs_review means
a person must confirm. NOTE: the upload endpoint also creates a scan.
"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

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
    out = ["Checked: " + (", ".join(_LABELS.get(c, c) for c in ran) if ran else "nothing") + "."]
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


def _find_visual(body: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(body, dict):
        return None
    detail = body.get("detail") if isinstance(body.get("detail"), dict) else {}
    for holder in (body.get("extraction"), detail.get("extraction"), detail):
        if isinstance(holder, dict) and isinstance(holder.get("visual"), dict):
            return holder["visual"]
    return None


async def explain_creative_visuals(client, file_bytes: bytes, filename: str,
                                   content_type: str = "application/octet-stream") -> str:
    if not file_bytes:
        return "No file was provided, so no visual check was run."
    try:
        async with client._client() as http:
            http.headers.pop("Content-Type", None)  # let httpx set the multipart boundary
            resp = await http.post("/api/scans/upload",
                                   files={"file": (filename, file_bytes, content_type)})
    except Exception as exc:  # noqa: BLE001
        logger.error("Visual check upload failed: %s", exc)
        return "The visual checks did not run because the backend could not be reached. This is not a pass."
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        body = None
    visual = _find_visual(body)
    if visual is not None:
        return explain_visual(visual)
    if resp.status_code not in (200, 201):
        return (f"The visual checks did not run: the backend rejected the file (HTTP {resp.status_code}). "
                "This is not a pass. A person needs to review it.")
    return explain_visual(None)
