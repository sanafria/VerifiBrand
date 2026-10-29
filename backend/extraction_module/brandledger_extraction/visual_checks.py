"""Visual brand checks (Member 5): colour, typography, layout, clearspace.
Entry point: run_visual_checks(data: bytes, filename: str, logo_bbox=None) -> VisualResult
Never raises; failures are reported in VisualResult.errors."""
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
from PIL import Image

from .visual_schema import VisualFinding, VisualResult

RULES_PATH = Path(__file__).with_name("brand_rules.json")


def load_rules() -> Dict[str, Any]:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb) -> str:
    return "#{:02X}{:02X}{:02X}".format(*[int(round(v)) for v in rgb])


def rgb_to_lab(rgb) -> np.ndarray:
    c = np.asarray(rgb, dtype=float) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = (c @ m.T) / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16.0 / 116.0)
    L = 116.0 * f[..., 1] - 16.0
    a = 500.0 * (f[..., 0] - f[..., 1])
    b = 200.0 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def _finding(category: str, rules: Dict[str, Any], **kw) -> VisualFinding:
    r = rules["rules"][category]
    return VisualFinding(policy_card_id=r["policy_card_id"], policy_version=r["policy_version"],
                         category=category, source_quote=r["quote"], **kw)


def _prepare_rgb(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img)
    return img.convert("RGB")


# ---------------------------------------------------------------- colour
def check_colour(img: Image.Image, rules: Dict[str, Any]) -> List[VisualFinding]:
    cfg = rules["colour"]
    names = list(rules["palette"])
    pal_rgb = np.array([_hex_to_rgb(rules["palette"][n]) for n in names], dtype=float)
    pal_lab = rgb_to_lab(pal_rgb)

    small = img.copy()
    small.thumbnail((200, 200))
    px = np.asarray(small, dtype=np.int32).reshape(-1, 3)
    keys = (px[:, 0] // 32) * 64 + (px[:, 1] // 32) * 8 + (px[:, 2] // 32)
    _, inv, counts = np.unique(keys, return_inverse=True, return_counts=True)
    inv = inv.ravel()
    means = np.stack([np.bincount(inv, weights=px[:, c]) / counts for c in range(3)], axis=1)
    shares = counts / float(len(px))

    if int((shares >= 0.01).sum()) > 12:   # photo / gradient: palette can't be judged reliably
        return [_finding(
            "visual_colour", rules, status="needs_review", severity="info",
            matched_text="Photographic or gradient-heavy image",
            explanation="Too many distinct colours to verify against the brand palette automatically.",
            suggested_fix="Have a reviewer confirm the colours manually.",
            confidence=0.5, evidence={"significant_colours": int((shares >= 0.01).sum())})]

    dists = np.linalg.norm(rgb_to_lab(means)[:, None, :] - pal_lab[None, :, :], axis=2)
    nearest, dmin = dists.argmin(axis=1), dists.min(axis=1)

    out: List[VisualFinding] = []
    for i in np.argsort(-shares):
        if shares[i] < cfg["min_area_share"] or len(out) >= 3:
            break
        de = float(dmin[i])
        if de <= cfg["delta_e_pass"]:
            continue
        hex_ = _rgb_to_hex(means[i])
        near = names[int(nearest[i])]
        is_fail = de > cfg["delta_e_review"]
        out.append(_finding(
            "visual_colour", rules,
            status="fail" if is_fail else "needs_review",
            severity="medium" if is_fail else "low",
            matched_text=f"{hex_} covering {shares[i]:.0%} of the image",
            explanation=f"{hex_} is not an approved palette colour (nearest: {near}, delta E {de:.1f}).",
            suggested_fix=f"Replace {hex_} with {near} ({rules['palette'][near]}).",
            confidence=0.9 if is_fail else 0.6,
            evidence={"colour": hex_, "area_share": round(float(shares[i]), 3),
                      "nearest": near, "delta_e": round(de, 1)}))
    return out


# ---------------------------------------------------------------- PDF text spans
def _pdf_spans(data: bytes) -> List[Dict[str, Any]]:
    import pymupdf
    doc = pymupdf.open(stream=data, filetype="pdf")
    spans = []
    for pno, page in enumerate(doc):
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                for s in line.get("spans", []):
                    t = s["text"].strip()
                    if t:
                        spans.append({"text": t, "font": s["font"], "size": float(s["size"]),
                                      "y": float(s["bbox"][1]), "page": pno,
                                      "bbox": [round(v, 1) for v in s["bbox"]]})
    doc.close()
    return spans


def _render_pdf_first_page(data: bytes) -> Image.Image:
    import pymupdf
    doc = pymupdf.open(stream=data, filetype="pdf")
    pix = doc[0].get_pixmap(alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return img


# ---------------------------------------------------------------- typography
def check_typography(spans: Sequence[Dict[str, Any]], rules: Dict[str, Any]) -> List[VisualFinding]:
    cfg = rules["typography"]
    allowed = [f.lower() for f in cfg["allowed_fonts"]]
    out: List[VisualFinding] = []
    seen = set()
    for s in spans:
        name = s["font"]
        if name in seen or any(a in name.lower() for a in allowed):
            continue
        seen.add(name)
        out.append(_finding(
            "visual_typography", rules, status="fail", severity="medium",
            matched_text=f"Font '{name}': \"{s['text'][:40]}\"",
            explanation=f"Font '{name}' is not an approved brand typeface.",
            suggested_fix="Use one of: " + ", ".join(cfg["allowed_fonts"]) + ".",
            confidence=0.9, evidence={"font": name, "page": s["page"], "bbox": s["bbox"]}))
    small = [s for s in spans if s["size"] < cfg["min_size_pt"]]
    if small:
        s = min(small, key=lambda x: x["size"])
        out.append(_finding(
            "visual_typography", rules, status="fail", severity="low",
            matched_text=f"{s['size']:.1f}pt text: \"{s['text'][:40]}\"",
            explanation=f"Text is {s['size']:.1f}pt; the minimum is {cfg['min_size_pt']}pt.",
            suggested_fix=f"Increase the text to at least {cfg['min_size_pt']}pt.",
            confidence=0.85, evidence={"size_pt": round(s["size"], 1), "count": len(small),
                                       "page": s["page"], "bbox": s["bbox"]}))
    return out


# ---------------------------------------------------------------- layout
def check_layout(spans: Sequence[Dict[str, Any]], rules: Dict[str, Any]) -> Optional[List[VisualFinding]]:
    """Returns None if the layout cannot be assessed (too little text)."""
    ratio = rules["layout"]["headline_to_body_ratio"]
    page = [s for s in spans if s["page"] == 0]
    if len(page) < 2:
        return None
    weight: Counter = Counter()
    for s in page:
        weight[round(s["size"], 1)] += len(s["text"])
    body = weight.most_common(1)[0][0]
    head = max(page, key=lambda s: (s["size"], -s["y"]))
    if body <= 0:
        return None
    got = head["size"] / body
    if got < ratio:
        return [_finding(
            "visual_layout", rules, status="fail", severity="medium",
            matched_text=f"Largest text {head['size']:.1f}pt vs body {body:.1f}pt",
            explanation=f"Headline is only {got:.2f}x body size; required at least {ratio}x.",
            suggested_fix="Make the headline clearly larger than the body text.",
            confidence=0.8, evidence={"headline_pt": round(head["size"], 1), "body_pt": body,
                                      "ratio": round(got, 2), "bbox": head["bbox"]})]
    bodies = [s for s in page if abs(s["size"] - body) < 0.6]
    if any(b["y"] < head["y"] for b in bodies):
        return [_finding(
            "visual_layout", rules, status="needs_review", severity="low",
            matched_text=f"Headline \"{head['text'][:40]}\" sits below some body text",
            explanation="The headline should be placed above the body text.",
            suggested_fix="Move the headline above the body copy.",
            confidence=0.6, evidence={"headline_y": round(head["y"], 1), "bbox": head["bbox"]})]
    return []


# ---------------------------------------------------------------- clearspace
def check_clearspace(img: Image.Image, logo_bbox: Sequence[int], rules: Dict[str, Any]) -> List[VisualFinding]:
    W, H = img.size
    x, y, w, h = [int(v) for v in logo_bbox]
    x, y = max(0, x), max(0, y)
    w, h = min(w, W - x), min(h, H - y)
    if w <= 0 or h <= 0:
        raise ValueError("logo_bbox is outside the image")
    req = max(1, int(round(rules["clearspace"]["multiple_of_logo_height"] * h)))
    arr = np.asarray(img, dtype=np.int16)
    border = np.concatenate([arr[0], arr[-1], arr[:, 0], arr[:, -1]])
    q = border // 16
    keys = q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2]
    vals, cnt = np.unique(keys, return_counts=True)
    bg = border[keys == vals[cnt.argmax()]].mean(axis=0)
    mask = np.abs(arr - bg).max(axis=2) > 40
    x0, y0, x1, y1 = max(0, x - req), max(0, y - req), min(W, x + w + req), min(H, y + h + req)
    region = mask[y0:y1, x0:x1].copy()
    region[y - y0:y + h - y0, x - x0:x + w - x0] = False
    ring = max(1, region.size - w * h)
    share = float(region.sum()) / ring
    out: List[VisualFinding] = []
    ev = {"bbox": [x, y, w, h], "required_px": req}
    if share > 0.002:
        out.append(_finding(
            "visual_clearspace", rules, status="fail", severity="medium",
            matched_text="Other content inside the logo clear space",
            explanation=f"Other content sits within {req}px of the logo (half its height).",
            suggested_fix="Move other elements away from the logo.",
            confidence=0.85, evidence={**ev, "intrusion_share": round(share, 4)}))
    margin = min(x, y, W - x - w, H - y - h)
    if margin < req:
        out.append(_finding(
            "visual_clearspace", rules, status="needs_review", severity="low",
            matched_text="Logo very close to the image edge",
            explanation=f"Only {margin}px between the logo and the edge; {req}px needed.",
            suggested_fix="Move the logo away from the edge.",
            confidence=0.6, evidence={**ev, "edge_margin_px": margin}))
    return out


# ---------------------------------------------------------------- entry point
def run_visual_checks(data: bytes, filename: str,
                      logo_bbox: Optional[Sequence[int]] = None) -> VisualResult:
    res = VisualResult(processed=False, image_hash=hashlib.sha256(data).hexdigest())
    try:
        rules = load_rules()
    except Exception as e:  # noqa: BLE001
        res.errors.append(f"rules load failed: {e}")
        return res

    is_pdf = filename.lower().endswith(".pdf")
    spans: List[Dict[str, Any]] = []
    try:
        if is_pdf:
            img = _prepare_rgb(_render_pdf_first_page(data))
            spans = _pdf_spans(data)
        else:
            img = _prepare_rgb(Image.open(io.BytesIO(data)))
    except Exception as e:  # noqa: BLE001
        res.errors.append(f"could not open file: {e}")
        return res
    res.processed = True

    def run(name, fn):
        try:
            res.findings.extend(fn())
            res.checks_run.append(name)
        except Exception as e:  # noqa: BLE001
            res.errors.append(f"{name} failed: {e}")

    run("visual_colour", lambda: check_colour(img, rules))

    if is_pdf:
        run("visual_typography", lambda: check_typography(spans, rules))
        lay = None
        try:
            lay = check_layout(spans, rules)
        except Exception as e:  # noqa: BLE001
            res.errors.append(f"visual_layout failed: {e}")
        if lay is None:
            if not any(e.startswith("visual_layout") for e in res.errors):
                res.skipped.append("visual_layout: not enough text to assess")
        else:
            res.findings.extend(lay)
            res.checks_run.append("visual_layout")
    else:
        res.skipped.append("visual_typography: fonts can only be read from PDFs")
        res.skipped.append("visual_layout: text sizes can only be read from PDFs")

    if logo_bbox is not None:
        run("visual_clearspace", lambda: check_clearspace(img, logo_bbox, rules))
    else:
        res.skipped.append("visual_clearspace: no logo location supplied")
    return res