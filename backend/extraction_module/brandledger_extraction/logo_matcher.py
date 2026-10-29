"""Compare an image against a library of reference logos.

What this does: reports whether the image *resembles* a reference logo
(shape similarity + colour distance).  What it does NOT do: approve a logo.
A high score only means "possible match" - a human must confirm.  Every result
carries ``human_review_required = True``.

Library layout (see logo_library/README.md):
    logo_library/manifest.json
    logo_library/approved/<file>.png
Each manifest entry has ``name``, ``file`` and ``status`` (approved | deprecated).
A match to a *deprecated* reference is reported as a possible outdated logo.
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

from . import config


@dataclass
class LogoReference:
    name: str
    status: str                 # approved | deprecated
    bgr: np.ndarray
    notes: str = ""
    placeholder: bool = False


def _load_image_with_alpha(path: Path) -> np.ndarray | None:
    if cv2 is None or np is None:
        return None
    data = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if data is None:
        return None
    if data.ndim == 2:
        return cv2.cvtColor(data, cv2.COLOR_GRAY2BGR)
    if data.shape[2] == 4:                       # composite transparent logos on white
        alpha = data[:, :, 3:4].astype(float) / 255.0
        return (data[:, :, :3] * alpha + 255 * (1 - alpha)).astype(np.uint8)
    return data


def load_library(library_dir: str | Path | None = None) -> tuple[list[LogoReference], list[str]]:
    """Load references. Returns (references, problems)."""
    if cv2 is None:
        return [], ["OpenCV (cv2) is not installed; logo matching disabled."]
    lib = Path(library_dir or config.LOGO_LIBRARY_DIR)
    manifest = lib / "manifest.json"
    problems: list[str] = []
    if not manifest.exists():
        return [], [f"No logo library manifest at {manifest}. See logo_library/README.md."]
    try:
        entries = json.loads(manifest.read_text(encoding="utf-8")).get("logos", [])
    except (OSError, ValueError) as exc:
        return [], [f"Could not read logo manifest: {exc}"]
    refs = []
    for e in entries:
        path = lib / e.get("file", "")
        img = _load_image_with_alpha(path) if path.is_file() else None
        if img is None:
            problems.append(f"Reference logo '{e.get('name')}' missing or unreadable: {path}")
            continue
        refs.append(LogoReference(e["name"], e.get("status", "approved"), img,
                                  e.get("notes", ""), bool(e.get("placeholder", False))))
    if not refs:
        problems.append("Logo library is empty - add approved logos to enable matching.")
    return refs, problems


# --------------------------------------------------------------- matching ----
def _edges(gray: np.ndarray) -> np.ndarray:
    g = cv2.GaussianBlur(gray, (3, 3), 0)
    e = cv2.Canny(g, 50, 150)
    return cv2.GaussianBlur(e, (5, 5), 0)         # tolerant to small misalignment


def _template_match(query_gray: np.ndarray, ref_gray: np.ndarray) -> tuple[float, tuple, float]:
    """Multi-scale edge template match -> (score, (x, y, w, h), scale)."""
    qh, qw = query_gray.shape
    q_edges = _edges(query_gray)
    best = (-1.0, (0, 0, 0, 0), 1.0)
    rh, rw = ref_gray.shape
    for frac in np.geomspace(0.06, 1.0, 70):
        tw = int(qw * frac)
        th = int(tw * rh / rw)
        if tw < 24 or th < 24 or tw > qw or th > qh:
            continue
        tmpl = cv2.resize(ref_gray, (tw, th), interpolation=cv2.INTER_AREA)
        res = cv2.matchTemplate(q_edges, _edges(tmpl), cv2.TM_CCOEFF_NORMED)
        _, score, _, loc = cv2.minMaxLoc(res)
        if score > best[0]:
            best = (float(score), (loc[0], loc[1], tw, th), tw / rw)
    return best


def _orb_inliers(query_gray: np.ndarray, ref_gray: np.ndarray) -> int:
    """Supporting evidence that survives rotation: RANSAC-verified ORB matches."""
    orb = cv2.ORB_create(nfeatures=1500)
    k1, d1 = orb.detectAndCompute(ref_gray, None)
    k2, d2 = orb.detectAndCompute(query_gray, None)
    if d1 is None or d2 is None or len(k1) < 8 or len(k2) < 8:
        return 0
    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(d1, d2, k=2)
    good = [p[0] for p in pairs if len(p) == 2 and p[0].distance < 0.75 * p[1].distance]
    if len(good) < 8:
        return 0
    src = np.float32([k1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([k2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    _, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    return int(mask.sum()) if mask is not None else 0


def _dominant_colour(bgr: np.ndarray) -> np.ndarray:
    """Mean colour of the pixels that differ from the background (border median)."""
    ring = np.concatenate([bgr[0], bgr[-1], bgr[:, 0], bgr[:, -1]]).astype(float)
    bg = np.median(ring, axis=0)
    flat = bgr.reshape(-1, 3).astype(float)
    dist = np.linalg.norm(flat - bg, axis=1)
    mask = dist > 40
    return flat[mask].mean(axis=0) if mask.sum() > 20 else flat.mean(axis=0)


def _delta_e(bgr1: np.ndarray, bgr2: np.ndarray) -> float:
    lab = lambda c: cv2.cvtColor(np.uint8([[np.clip(c, 0, 255)]]), cv2.COLOR_BGR2LAB)[0, 0].astype(float)
    return float(np.linalg.norm(lab(bgr1) - lab(bgr2)))


def _downscale(bgr: np.ndarray, longest: int = 1000) -> tuple[np.ndarray, float]:
    h, w = bgr.shape[:2]
    if max(h, w) <= longest:
        return bgr, 1.0
    s = longest / max(h, w)
    return cv2.resize(bgr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), s



def _fg_mask(bgr: np.ndarray) -> np.ndarray:
    """Foreground = pixels clearly different from the border-median background."""
    ring = np.concatenate([bgr[0], bgr[-1], bgr[:, 0], bgr[:, -1]]).astype(float)
    bg = np.median(ring, axis=0)
    dist = np.linalg.norm(bgr.astype(float) - bg, axis=2)
    return (dist > 40).astype(np.uint8)


def _mask_similarity(query_bgr: np.ndarray, ref_bgr: np.ndarray, size: int = 128):
    """Scale-independent shape comparison of two standalone logos (IoU of filled masks).
    Returns (score, bbox in query coords) or (0, None) when no foreground is found."""
    qm, rm = _fg_mask(query_bgr), _fg_mask(ref_bgr)
    if qm.sum() < 50 or rm.sum() < 50:
        return 0.0, None
    def norm(m):
        ys, xs = np.where(m)
        crop = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        h, w = crop.shape
        s = (size - 8) / max(h, w)
        crop = cv2.resize(crop, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA)
        canvas = np.zeros((size, size), np.uint8)
        y0, x0 = (size - crop.shape[0]) // 2, (size - crop.shape[1]) // 2
        canvas[y0:y0 + crop.shape[0], x0:x0 + crop.shape[1]] = crop > 0
        return canvas, (xs.min(), ys.min(), w, h)
    a, bbox = norm(qm)
    b, _ = norm(rm)
    inter, union = np.logical_and(a, b).sum(), np.logical_or(a, b).sum()
    return float(inter / union) if union else 0.0, bbox

def match_logos(bgr: np.ndarray, references: list[LogoReference], page=None, has_text: bool = False) -> list[dict]:
    """Compare ``bgr`` with each reference. Returns one result per reference,
    best first.  Never raises for ordinary images."""
    if cv2 is None or not references:
        return []
    original_h, original_w = bgr.shape[:2]
    query, scale = _downscale(bgr)
    q_gray = cv2.cvtColor(query, cv2.COLOR_BGR2GRAY)
    standalone = (max(original_h, original_w) <= config.LOGO_STANDALONE_MAX_SIDE) and not has_text
    results = []
    for ref in references:
        r_gray = cv2.cvtColor(ref.bgr, cv2.COLOR_BGR2GRAY)
        # Pad so a standalone logo file with tight margins can still be matched
        pad = int(0.1 * max(q_gray.shape))
        padded_q = cv2.copyMakeBorder(q_gray, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
        padded_c = cv2.copyMakeBorder(query, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
        t_score, (x, y, w, h), _ = _template_match(padded_q, r_gray)
        inliers = _orb_inliers(q_gray, r_gray)
        shape_score = max(t_score, min(1.0, inliers / 30.0))
        if standalone:
            m_score, bbox = _mask_similarity(query, ref.bgr)
            if m_score > shape_score and bbox is not None:
                shape_score = m_score
                x, y, w, h = bbox[0] + pad, bbox[1] + pad, bbox[2], bbox[3]
        shape_score = float(max(0.0, min(1.0, shape_score)))

        delta_e = None
        if w > 0:
            region = padded_c[y:y + h, x:x + w]
            if region.size:
                delta_e = _delta_e(_dominant_colour(region), _dominant_colour(ref.bgr))

        result = _classify(ref, shape_score, delta_e, standalone)
        result.update({
            "reference_name": ref.name, "reference_status": ref.status,
            "similarity_score": round(shape_score, 3),
            "colour_delta_e": None if delta_e is None else round(delta_e, 1),
            "orb_inliers": inliers, "page": page,
            "region": {"x": max(0, x - pad), "y": max(0, y - pad), "w": w, "h": h} if w else None,
            "placeholder_reference": ref.placeholder,
            "region_full": ({"x": int(round(max(0, x - pad) / scale)), "y": int(round(max(0, y - pad) / scale)),
                             "w": int(round(w / scale)), "h": int(round(h / scale))} if w else None),
            "image_size": {"w": int(original_w), "h": int(original_h)},
            "human_review_required": True,
        })
        results.append(result)
    results.sort(key=lambda r: r["similarity_score"], reverse=True)
    return results


def _classify(ref: LogoReference, score: float, delta_e, standalone: bool) -> dict:
    colour_off = delta_e is not None and delta_e > config.LOGO_COLOR_DELTA_E
    if score >= config.LOGO_MATCH_THRESHOLD:
        if ref.status == "deprecated":
            return {"status": "possible_outdated_logo", "explanation":
                    f"The image resembles '{ref.name}', which is marked DEPRECATED in the logo library "
                    f"(similarity {score:.2f}). It may be an outdated logo. A human must confirm."}
        if colour_off:
            return {"status": "possible_variant_mismatch", "explanation":
                    f"The shape resembles approved logo '{ref.name}' (similarity {score:.2f}) but the "
                    f"colours differ noticeably (colour distance {delta_e:.0f}). It may be an unapproved "
                    "recolour or a different variant. A human must confirm."}
        return {"status": "possible_match", "explanation":
                f"The image resembles approved logo '{ref.name}' (similarity {score:.2f}). This is a "
                "visual similarity only, not proof the logo is correct or correctly used. A human must confirm."}
    if score >= config.LOGO_UNCERTAIN_THRESHOLD:
        return {"status": "uncertain", "explanation":
                f"Weak resemblance to '{ref.name}' (similarity {score:.2f}). Cannot tell whether this "
                "is the approved logo; please check manually."}
    if standalone:
        return {"status": "no_match", "explanation":
                f"This logo-sized image does not resemble '{ref.name}' (similarity {score:.2f}). "
                "It may be a wrong or unapproved logo."}
    return {"status": "not_found", "explanation":
            f"No region resembling '{ref.name}' was found (similarity {score:.2f}). This does not prove "
            "the logo is absent or wrong - the detector only looks for known reference logos."}


def summarise_logo_results(per_reference: list[dict]) -> dict | None:
    """Pick the single most informative result across all references.

    Among references scoring within 0.05 of the best, prefer a clean approved
    match over a variant mismatch / deprecated hit, so a correct logo is not
    reported against the wrong (e.g. monochrome) reference.
    """
    if not per_reference:
        return None
    priority = {"possible_match": 5, "possible_outdated_logo": 4, "possible_variant_mismatch": 3.5,
                "uncertain": 3, "no_match": 2, "not_found": 1}
    top = max(r["similarity_score"] for r in per_reference)
    close = [r for r in per_reference if r["similarity_score"] >= top - 0.05]
    return max(close, key=lambda r: (priority.get(r["status"], 0), r["similarity_score"]))
