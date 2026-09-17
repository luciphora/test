# The report — structure, tokens, and the mistakes to check for

## Section order that worked
1. Masthead: one-line verdict as the H1, the question as the deck, 3–4 pills with the headline percentages *and their previous values*.
2. **What changed since the last snapshot** — deaths and launches in the window, the active-count sparkline, the tenure-at-death table with data-derived labels.
3. Funnel cards (generated from data).
4. Waves table: launch → live now → re-fund → latest wave, per segment.
5. Cohort survival by vertical, restricted to one launch week so tenure is comparable; a "this window" column.
6. Same-script-swapped-noun quote pairs (won / lost).
7. Hook families with survival; the counter-intuitive one called out in a note.
8. Longest-running control set: table + cards.
9. Creative gallery: live featured ads, then killed ones — latest cull first, badge shows the window and real tenure.
10. Transcript browser: search + status/funnel/vertical filters. Every live ad plus every featured-funnel dead ad inline; the rest ship in the zip.
11. Method and limits. 12. Four takeaways.

## Design
Cool slate neutrals; green/rust semantic pair for live/killed (not the accent); brass hairlines for structure. Archivo (display, 700–800, tight), Public Sans (body), IBM Plex Mono (data, badges, URLs). Three-state theme tokens on `:root`, `prefers-color-scheme` guarded by `:root:not([data-theme="light"])`, and `:root[data-theme="dark"]`. Survival as in-table bars. Sparkline as inline SVG at a viewBox wide enough for the container (1080×110), value label left of the endpoint. `report.css` / `report.js` / `report_body.html` in the last target are the starting point — copy, then rewrite the prose.

## Validation is not optional
`validate_report.py` checks placeholders, U+FFFD, tag balance, cards without stills, wrapper tags, size, and renders in the bundled Chromium (`/opt/pw-browsers/chromium-1194/chrome-linux/chrome`; the pip Playwright's own browser is a different build and won't launch). Then look at the screenshots — two of the three refreshes shipped a table that read wrong until a screenshot caught it.

## Mistakes already made once
- A "this window" column that counted deaths across *all* windows. Scope every window figure to `died_between == [SNAP, NOW]`.
- Figures typed into `brief.md` by hand that disagreed with the report. Everything numeric comes from the same `ads.json`.
- `transcripts/` never cleared between runs, so ads that died existed as both `live-…` and `dead-…` files. The compiler now wipes first; check `ls transcripts | sed 's/.*-//' | sort | uniq -d` is empty.
- Only reading `thumbnail`; image ads and carousels have their still elsewhere.
- Trusting `running_duration` on dead ads.
- Declaring a niche a winner on one snapshot. Wave 2 looked like a re-fund verdict; the next snapshot showed it dead in 48 hours.
