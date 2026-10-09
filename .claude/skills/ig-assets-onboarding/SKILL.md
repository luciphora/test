---
name: ig-assets-onboarding
description: Onboard an Instagram account's assets and access for a new client (or a brand relaunch) — collect, spec-check, organize, and gap-list everything needed to start posting. Covers secure account access (Meta partner access, never passwords), brand kit, profile assets, content library, strategy inputs, a folder structure + naming convention, an automated spec audit of received files, an onboarding tracker, and a drafted "what we still need" request to the client. Use this whenever someone mentions IG/Instagram onboarding, a new social client, "collect their assets", "brand kit intake", "set up their Instagram folder", "what do we need from the client to start posting", auditing a dump of client photos/videos for Instagram, or kicking off content for a newly signed account — even if they don't say "onboarding".
---

# Instagram Assets Onboarding

Goal: go from "client just signed" to "we can post next week" with nothing missing and nothing insecure. The output is a tidy asset library, an onboarding tracker that shows what's in and what's missing, and a ready-to-send request for the gaps.

The order below matters: access first (it has the longest lead time and blocks everything), then inventory what already exists before asking the client for anything — clients lose patience fast when asked for things they already sent.

## 0. Frame the onboarding

Pin these down from the conversation, the signed proposal, or a quick question. Don't block on anything you can fill in later — mark it `TBD` in the tracker.

- **Account**: client/brand name, IG handle, account type (Business or Creator), linked Facebook Page
- **Where assets live now**: Google Drive folder, Shade drive, Dropbox/WeTransfer link, or a local folder
- **Where the library should live**: default to the same system the team already uses (check for an existing clients folder in Drive or Shade before creating a new root)
- **Scope**: organic only, or ads too (ads add ad-account + pixel access); scheduler in use (e.g. Postiz, Later, Meta Business Suite)
- **Target first-post date** — drives what counts as "blocking" vs "nice to have"
- **Internal owner** for the onboarding (who chases the client)

## 1. Access — do this first

Read `references/access.md` for the exact steps. Key principles, because a leaked IG login can cost a client their account:

- Request **partner access through Meta Business Suite / Business Portfolio** — the client approves it, nobody shares a password. Request the narrowest role that does the job.
- If a password truly must be shared (e.g. a personal Creator account with no Business Portfolio), it goes through a password manager share, never chat, email, Notion, or a doc. Don't write passwords or 2FA codes anywhere in the tracker — log *that* access exists and *how*, not the secret itself.
- Log every access grant in the tracker's Access table: what, role, granted by, date.

## 2. Inventory what already exists

Before asking for anything, look at what's already been sent.

1. Pull together everything received (folder, shared links, email attachments) into one staging location.
2. Run the spec audit:
   ```bash
   python scripts/inventory.py <assets_dir> --out <output_dir>
   ```
   It walks the folder, classifies each file (logo, photo, video, font, doc, …), checks images/videos against Instagram specs, flags duplicates, HEIC/low-res/wrong-aspect files, and writes `inventory.md` + `inventory.json`. Needs Pillow; uses `ffprobe` for video if available.
3. Read `inventory.md`. Its "Needs attention" list is what you fix (convert, re-request in higher res) — not the whole inventory.

The spec reference lives in `references/ig-specs.md`. Instagram changes specs often — if a decision hinges on a number (aspect ratio, Reel length, carousel count, hashtag cap), check the date at the top of that file and re-verify against current Instagram help docs if it's older than ~6 months.

## 3. Map received assets against the checklist

Read `references/checklist.md`. It's grouped by tier:

- **Tier 1 — blocking**: can't post without it (access, logo, colors, profile photo, bio/link, enough content for the first 2 weeks, approval workflow)
- **Tier 2 — needed in the first month**: highlight covers, fonts, testimonials, past top posts, competitor/inspo accounts
- **Tier 3 — nice to have**: brand guidelines PDF, raw b-roll archive, press kit

For each item mark: ✅ received · ⚠️ received but needs fixing (say what) · ❌ missing · ➖ not applicable.

## 4. Organize the library

Create this structure (in Drive, Shade, or locally — whichever was chosen in step 0) and move/copy files into it:

```
<Client> — Instagram/
├── 00_Admin/              onboarding tracker, access log (no secrets), approvals
├── 01_Brand/
│   ├── logos/             primary, secondary, mark; light + dark; SVG + PNG
│   ├── colors-fonts/      palette (hex), font files or names + licenses
│   └── guidelines/        brand guide, voice & tone, do/don't words
├── 02_Profile/            profile photo, highlight covers, bio.md, link-in-bio
├── 03_Library/
│   ├── photos/            headshots/ lifestyle/ product/ bts/
│   ├── video/             raw/ broll/ edited/
│   └── testimonials/      screenshots + written permission
├── 04_Templates/          Canva/Figma links, carousel + story templates
├── 05_Reference/          past-top-posts/ inspo/ competitors/
└── 06_Ready-to-post/      approved, spec-correct, captioned
```

Rename files on the way in: `client_category_descriptor_YYYYMMDD_v01.ext` (lowercase, hyphens inside parts, e.g. `acme_headshot_founder-studio_20261009_v01.jpg`). Consistent names make the library searchable and stop "final_FINAL2.jpg" chaos. Keep originals untouched — don't overwrite or delete what the client sent; copy into the structure and leave the staging folder as the archive.

Ask before moving or renaming files in a client's own shared folder — reorganizing their space can break their links. Organizing inside the team's own library is fine.

## 5. Write the onboarding tracker

Save it as `00_Admin/onboarding-tracker.md` (or as a Notion page / Google Doc if that's where the team tracks clients). Use this template:

```markdown
# <Client> — Instagram Onboarding
Handle: @<handle> · Type: <Business/Creator> · Owner: <name> · First post target: <date>
Status: <Blocked on X | Ready to start content | Complete>

## Access
| What | Role / level | Method | Granted by | Date | Status |
|------|--------------|--------|-----------|------|--------|

## Asset checklist
| Tier | Item | Status | Location / note |
|------|------|--------|-----------------|

## Needs attention (from spec audit)
- <file> — <problem> — <fix>

## Strategy inputs
Audience · Offers & CTAs · Content pillars · Voice notes · Off-limits topics · Approval workflow (who approves, turnaround)

## Open questions
- ...
```

Status line rule: if any Tier 1 item is ❌, status is "Blocked on <item>". That one line is what the team reads first.

## 6. Draft the gap request to the client

One message, not a drip of follow-ups. Group asks by tier, blocking first, each with *exactly* what format/size you need and why in a few words. Lead with what you already have so the client sees progress.

Template:

```
Subject: <Brand> Instagram — last few things we need to launch

Hi <first name>,

We've got your <short list of what's in> organized and ready. To hit <first-post date>, we need:

Needed before we can post:
1. <item> — <format/spec> (<why, 5 words>)
2. ...

Needed in the first month:
3. ...

Easiest way to send: drop files in <upload link>. For Instagram access, approve the partner request we sent from Meta Business Suite — no passwords needed.

Thanks,
<sender>
```

Create it as a **draft** (Gmail draft if connected, otherwise in the tracker). Don't send it — the sender reviews tone and the ask list first.

## 7. Hand back

Report in a few lines: the tracker status line, counts (received / needs fixing / missing by tier), where the library and tracker live, and that the client request is drafted and waiting for review. Link to files rather than pasting them.

## Notes

- Testimonials and photos of other people need permission before posting; note in the tracker whether permission is on file.
- Fonts: record the license. A brand font the client "just has installed" may not be licensed for the team's use; if unclear, flag it and note a free fallback.
- If the client has nothing (brand new account), the checklist turns into a creation plan — mark items ❌ and add who will produce each one instead of requesting it.
