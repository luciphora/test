# Instagram asset specs

_Last verified: 2026-10. Instagram changes these often — re-check Instagram/Meta help docs for anything decision-critical if this date is more than ~6 months old._

These same numbers drive `scripts/inventory.py`; update both together.

## Feed posts (single image + carousel)

| Format | Aspect | Recommended px | Notes |
|--------|--------|----------------|-------|
| Portrait (tall) | 3:4 | 1080×1440 | Matches the profile grid's 3:4 preview |
| Portrait | 4:5 | 1080×1350 | Still fully supported; grid crops it slightly |
| Square | 1:1 | 1080×1080 | |
| Landscape | 1.91:1 | 1080×566 | Small in feed; avoid for primary content |

- Minimum width for crisp display: 1080 px. Anything under ~720 px on the short side looks soft.
- Carousels: up to 20 slides; all slides share the first slide's aspect ratio.
- Keep text and faces inside the center 3:4 area so the grid crop doesn't cut them.

## Stories & Reels

| Item | Aspect | Recommended px | Notes |
|------|--------|----------------|-------|
| Story / Reel | 9:16 | 1080×1920 | Keep text ~250 px clear of top and bottom (UI overlays) |
| Reel cover | 9:16 | 1080×1920 | Grid shows a center 3:4 crop |
| Highlight cover | 9:16 | 1080×1920 | Icon centered; shown as a small circle |

- Reels: up to 3 minutes. MP4 or MOV, H.264 (HEVC accepted), AAC audio, 30 fps (24–60 fine).
- Upload the original file, not a screen recording or a re-downloaded copy — re-compression shows.

## Profile

| Item | Spec |
|------|------|
| Profile photo | Upload ≥320×320 (1080×1080 recommended), square, subject centered — displayed as a small circle |
| Bio | ≤150 characters |
| Links | Up to 5 links in bio |
| Name field | Searchable — include a keyword, not just the brand name |

## Captions

- Caption up to 2,200 characters; first ~125 show before "more".
- Hashtags: Instagram has been tightening hashtag limits (it moved toward a small cap, ~5, in late 2025). Verify the current limit before building a hashtag strategy.

## File hygiene

- HEIC (iPhone default) → convert to JPG/PNG before scheduling; many tools reject it.
- sRGB color profile for images; CMYK files from print designers will look off.
- Logos: transparent PNG for overlays; SVG/PDF as the master.
