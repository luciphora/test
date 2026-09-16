# Vendored skills

Third-party skills copied in unmodified. Keeping them verbatim is deliberate: it
means a later `git diff` against upstream shows only what upstream changed, so
they can be refreshed without untangling local edits.

| Skill | Upstream | Commit | Licence |
|---|---|---|---|
| `grilling` | [mattpocock/skills](https://github.com/mattpocock/skills) `skills/productivity/grilling` | `959a8e9f1edc3adbe2f7e3054bb6fbefa6696260` | MIT, © Matt Pocock |
| `wait-what` | [mattpocock/skills](https://github.com/mattpocock/skills) `skills/productivity/wait-what` | `959a8e9f1edc3adbe2f7e3054bb6fbefa6696260` | MIT, © Matt Pocock |

To refresh: re-copy from the same paths upstream and bump the commit above.

## Known gap

`wait-what` tells the agent to use the ubiquitous language from `CONTEXT.md`
(via `CONTEXT-MAP.md` when a repo has several). Neither file exists in this
repo, so that clause currently points at nothing — the skill still works, it
just falls back to plain language. Left as-is rather than patched, so the file
stays diffable against upstream.
