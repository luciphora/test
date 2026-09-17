# Delivery — where things go, and how to know they arrived

**Read back, always.** A send is done when the thing is seen at the destination — the DM history shows the file, the page loads, the commit is on the remote. Not when the tool returns `ok: true`. This holds *especially* after a cancel, reject, or error: the Composio sandbox posted a zip to Slack after the call was reported as rejected. Check the footprint before reporting the outcome.

**Artifacts are private by default.** Share from the page's menu before the link goes to anyone else. If that needs Moe's click, say so in the message that carries the link.

**Slack goes through Composio**, never the Slack MCP connector. Open the DM with `SLACK_OPEN_DM` (user id → `D…` channel id), then:
- **Text** (`.md`, `.csv`, `.txt`) → `SLACK_UPLOAD_OR_CREATE_A_FILE_IN_SLACK` with `content` + `filename` + `channels`. Direct.
- **Binary** (`.zip`, `.mp4`, `.pdf`) → the tool needs an `s3key`, so stage first in `COMPOSIO_REMOTE_WORKBENCH`: fetch the file from a public URL (the repo branch archive works), `upload_local_file(path)` → `s3key`, then `run_composio_tool("SLACK_UPLOAD_OR_CREATE_A_FILE_IN_SLACK", {"file": {"name","mimetype","s3key"}, "channels": …})`. Rebuilding from the public branch beats moving bytes through context.
- **Verify** with `SLACK_FETCH_CONVERSATION_HISTORY` on the `D…` channel; the upload response's `channels`/`ims` are empty even on success, so don't read them.

**Chat delivery** (`SendUserFile`) caps at 30 MB per file. Zipping compressed media doesn't help. Send the longest-running clips first, renamed `<days>d-<id>.mp4`, and name what couldn't go.

**GitHub** is the durable copy of code and skills. The repo is public, so a branch archive URL is a legitimate transport for a sandbox to fetch from.
