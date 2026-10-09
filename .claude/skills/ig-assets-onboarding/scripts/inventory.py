#!/usr/bin/env python3
"""Inventory a folder of client assets and check them against Instagram specs.

Usage:
    python inventory.py <assets_dir> [--out <output_dir>]

Writes inventory.md (human summary + "Needs attention" list) and inventory.json
(one record per file) to --out (default: current directory).

Requires Pillow for images. Uses ffprobe (if on PATH) for video metadata.
Keep thresholds in sync with references/ig-specs.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".bmp"}
HEIC_EXT = {".heic", ".heif"}
VECTOR_EXT = {".svg", ".eps", ".ai"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
FONT_EXT = {".ttf", ".otf", ".woff", ".woff2"}
DOC_EXT = {".pdf", ".doc", ".docx", ".txt", ".md", ".pages", ".key", ".ppt", ".pptx", ".csv", ".xlsx"}
DESIGN_EXT = {".psd", ".fig", ".sketch", ".indd", ".xd"}
IGNORE = {".ds_store", "thumbs.db", "desktop.ini"}

# Aspect targets (width / height) from references/ig-specs.md
ASPECTS = {
    "9:16 (story/reel)": 9 / 16,
    "3:4 (feed portrait)": 3 / 4,
    "4:5 (feed portrait)": 4 / 5,
    "1:1 (square)": 1.0,
    "1.91:1 (feed landscape)": 1.91,
}
ASPECT_TOLERANCE = 0.03  # relative
MIN_SHORT_SIDE = 1080      # crisp feed/story
SOFT_SHORT_SIDE = 720      # below this: request higher res
MIN_PROFILE = 320
MAX_REEL_SECONDS = 180

# Filename/folder keywords -> category. First match wins, so order matters.
KEYWORDS = [
    ("logo", ("logo", "wordmark", "monogram", "brandmark", "mark_", "-mark", "icon")),
    ("profile", ("profile", "avatar", "pfp")),
    ("highlight-cover", ("highlight",)),
    ("headshot", ("headshot", "portrait", "head-shot")),
    ("testimonial", ("testimonial", "review", "feedback")),
    ("product", ("product", "packshot")),
    ("bts", ("bts", "behind", "process")),
    ("lifestyle", ("lifestyle",)),
    ("screenshot", ("screenshot", "screen shot", "screen_shot")),
    ("guidelines", ("guideline", "brand-guide", "brand_guide", "brandbook", "style-guide", "styleguide")),
    ("template", ("template",)),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def keyword_category(rel: str) -> str | None:
    low = rel.lower()
    for cat, words in KEYWORDS:
        if any(w in low for w in words):
            return cat
    return None


def closest_aspect(w: int, h: int) -> tuple[str | None, float]:
    ratio = w / h
    best, best_err = None, 1e9
    for name, target in ASPECTS.items():
        err = abs(ratio - target) / target
        if err < best_err:
            best, best_err = name, err
    return (best if best_err <= ASPECT_TOLERANCE else None), ratio


def probe_video(path: Path) -> dict:
    if not shutil.which("ffprobe"):
        return {}
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,codec_name,r_frame_rate:format=duration",
             "-of", "json", str(path)],
            capture_output=True, text=True, timeout=60, check=True,
        )
        data = json.loads(out.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return {"error": "ffprobe failed"}
    stream = (data.get("streams") or [{}])[0]
    fps = None
    if "/" in str(stream.get("r_frame_rate", "")):
        num, den = stream["r_frame_rate"].split("/")
        fps = round(float(num) / float(den), 2) if float(den) else None
    dur = data.get("format", {}).get("duration")
    return {
        "width": stream.get("width"),
        "height": stream.get("height"),
        "codec": stream.get("codec_name"),
        "fps": fps,
        "duration_s": round(float(dur), 1) if dur else None,
    }


def check_visual(rec: dict, w: int, h: int, category: str) -> None:
    """Fill aspect/fit fields and append issues for an image or video frame size."""
    aspect, ratio = closest_aspect(w, h)
    short = min(w, h)
    rec.update(width=w, height=h, aspect=aspect or f"{ratio:.2f}:1 (non-standard)")
    issues = rec["issues"]

    if category in ("logo",):
        if short < 500:
            issues.append(f"logo is only {w}x{h} — request vector (SVG/PDF) or ≥1000 px PNG")
        return
    if category == "profile":
        if short < MIN_PROFILE:
            issues.append(f"profile photo {w}x{h} is below {MIN_PROFILE} px minimum")
        elif short < MIN_SHORT_SIDE:
            issues.append(f"profile photo {w}x{h} — 1080x1080 recommended")
        if aspect != "1:1 (square)":
            issues.append("profile photo is not square — will be cropped to a circle")
        return

    if short < SOFT_SHORT_SIDE:
        issues.append(f"low resolution ({w}x{h}) — request original/higher-res file")
    elif short < MIN_SHORT_SIDE and not (aspect and "1.91" in aspect):
        issues.append(f"below 1080 px on short side ({w}x{h}) — usable but soft")
    if aspect is None:
        issues.append(f"non-standard aspect {ratio:.2f}:1 — will need cropping for IG")

    fits = []
    if aspect == "9:16 (story/reel)":
        fits = ["story", "reel", "highlight-cover"]
    elif aspect in ("3:4 (feed portrait)", "4:5 (feed portrait)", "1:1 (square)", "1.91:1 (feed landscape)"):
        fits = ["feed"]
    rec["fits"] = fits


def scan(root: Path) -> list[dict]:
    records = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.name.lower() in IGNORE or path.name.startswith("._"):
            continue
        rel = str(path.relative_to(root))
        ext = path.suffix.lower()
        kw = keyword_category(rel)
        rec = {"path": rel, "ext": ext, "bytes": path.stat().st_size,
               "sha256": sha256(path), "issues": [], "fits": []}

        if ext in IMAGE_EXT:
            rec["type"] = "image"
            rec["category"] = kw or "photo"
            if Image is None:
                rec["issues"].append("Pillow not installed — dimensions not checked")
            else:
                try:
                    with Image.open(path) as im:
                        w, h = im.size
                        mode = im.mode
                        icc = im.info.get("icc_profile")
                    check_visual(rec, w, h, rec["category"])
                    if mode == "CMYK":
                        rec["issues"].append("CMYK color — convert to sRGB")
                    if rec["category"] == "logo" and ext in (".jpg", ".jpeg"):
                        rec["issues"].append("logo is JPG (no transparency) — request PNG/SVG")
                    rec["has_icc"] = bool(icc)
                except Exception as e:  # corrupt or unsupported
                    rec["issues"].append(f"could not open image: {e.__class__.__name__}")
        elif ext in HEIC_EXT:
            rec["type"] = "image"
            rec["category"] = kw or "photo"
            rec["issues"].append("HEIC — convert to JPG before scheduling")
        elif ext in VECTOR_EXT:
            rec["type"] = "vector"
            rec["category"] = kw or "logo"
        elif ext in VIDEO_EXT:
            rec["type"] = "video"
            rec["category"] = kw if kw in ("testimonial", "bts", "product", "lifestyle", "screenshot") else "video"
            meta = probe_video(path)
            rec.update({k: v for k, v in meta.items() if k not in ("width", "height")})
            if meta.get("width") and meta.get("height"):
                check_visual(rec, meta["width"], meta["height"], rec["category"])
            elif not meta:
                rec["issues"].append("ffprobe not available — video not checked")
            dur = meta.get("duration_s")
            if dur and dur > MAX_REEL_SECONDS:
                rec["issues"].append(f"{dur:.0f}s long — over {MAX_REEL_SECONDS}s Reel limit; raw footage or needs cutting")
            if ext in (".avi", ".mkv", ".webm"):
                rec["issues"].append(f"{ext} — convert to MP4 (H.264) for upload")
        elif ext in FONT_EXT:
            rec["type"] = "font"
            rec["category"] = "font"
            rec["issues"].append("confirm font license covers agency use")
        elif ext in DESIGN_EXT:
            rec["type"] = "design-source"
            rec["category"] = kw or "design-source"
        elif ext in DOC_EXT:
            rec["type"] = "document"
            rec["category"] = kw or "document"
        else:
            rec["type"] = "other"
            rec["category"] = kw or "other"
            rec["issues"].append(f"unrecognized file type {ext or '(none)'}")

        if rec["category"] == "screenshot" and rec["type"] in ("image", "video"):
            rec["issues"].append("screenshot/screen recording — request original file if this is meant as content")
        records.append(rec)

    # First file (in sorted order) with a given hash is the original; later ones are duplicates.
    first_seen: dict[str, str] = {}
    for r in records:
        if r["bytes"] == 0:
            r["issues"].append("empty file (0 bytes) — upload likely failed; re-request")
            continue
        original = first_seen.setdefault(r["sha256"], r["path"])
        if original != r["path"]:
            r["duplicate_of"] = original
            r["issues"].append(f"duplicate of {original} — skip")
    return records


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def write_markdown(records: list[dict], root: Path, out: Path) -> None:
    cats = Counter(r["category"] for r in records)
    types = Counter(r["type"] for r in records)
    fits = Counter(f for r in records for f in r.get("fits", []) if not r["issues"])
    flagged = [r for r in records if r["issues"]]

    lines = [
        f"# Asset inventory — {root.name}",
        f"_Generated {date.today().isoformat()} · {len(records)} files · "
        f"{human_size(sum(r['bytes'] for r in records))} · {len(flagged)} need attention_",
        "",
        "## Summary by category",
        "| Category | Files |",
        "|----------|-------|",
        *[f"| {c} | {n} |" for c, n in cats.most_common()],
        "",
        "## Summary by type",
        ", ".join(f"{t}: {n}" for t, n in types.most_common()) or "(none)",
        "",
        "## Ready-to-use content (no issues)",
        f"- Feed-ready: {fits.get('feed', 0)}",
        f"- Story/Reel-ready (9:16): {fits.get('story', 0)}",
        "",
        "## Needs attention",
    ]
    if flagged:
        for r in flagged:
            lines.append(f"- `{r['path']}` — " + "; ".join(r["issues"]))
    else:
        lines.append("Nothing flagged.")
    lines += ["", "## All files", "| File | Type | Category | Size | Dims | Aspect / duration |",
              "|------|------|----------|------|------|-------------------|"]
    for r in records:
        dims = f"{r['width']}x{r['height']}" if r.get("width") else ""
        extra = r.get("aspect", "")
        if r.get("duration_s"):
            extra = f"{extra} · {r['duration_s']}s".strip(" ·")
        lines.append(f"| `{r['path']}` | {r['type']} | {r['category']} | {human_size(r['bytes'])} | {dims} | {extra} |")
    (out / "inventory.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("assets_dir", type=Path)
    ap.add_argument("--out", type=Path, default=Path("."))
    args = ap.parse_args()

    if not args.assets_dir.is_dir():
        print(f"error: {args.assets_dir} is not a directory", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)

    records = scan(args.assets_dir)
    (args.out / "inventory.json").write_text(json.dumps(records, indent=2))
    write_markdown(records, args.assets_dir, args.out)

    flagged = sum(1 for r in records if r["issues"])
    print(f"{len(records)} files scanned, {flagged} need attention → {args.out / 'inventory.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
