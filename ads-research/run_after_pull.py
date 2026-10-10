#!/usr/bin/env python3
"""Everything after the Foreplay pull, in order, for one target.

    python run_after_pull.py targets/<slug> --pages targets/<slug>/pages_<date>            # first pull
    python run_after_pull.py targets/<slug> --pages targets/<slug>/pages_<date> \\
                             --snap 2026-09-01 --now 2026-09-03                              # refresh

First pull: consolidate pages into ads.json. Refresh: overlay the new pages on
the existing ads.json so ads that vanished get a real stop window. Then classify
against <target>/taxonomy.py, fetch stills, compile transcripts, build the
report, validate it. Stops at the first failing step.
"""
import argparse, subprocess, sys, os, shutil, datetime

def run(*cmd, cwd=None):
    print("\n$", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode: sys.exit(f"step failed: {cmd[1] if len(cmd)>1 else cmd[0]}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target"); ap.add_argument("--pages", help="pages dir from a previous collect; omit when using --page-id")
    ap.add_argument("--page-id", help="collect first via collect_foreplay.py (needs FOREPLAY_API_KEY), then process")
    ap.add_argument("--snap", help="date of the snapshot being refreshed (omit on first pull)")
    ap.add_argument("--now", default=datetime.date.today().isoformat())
    a = ap.parse_args(); here = os.path.dirname(os.path.abspath(__file__)); t = a.target
    py = sys.executable
    if a.page_id:
        a.pages = os.path.join(t, f"pages_{a.now.replace('-', '')[4:]}")
        run(py, f"{here}/collect_foreplay.py", a.page_id, t, "--yes", "--date", a.now, *(["--since", a.snap] if a.snap else []))
    elif not a.pages:
        sys.exit("pass --pages <dir> (existing pull) or --page-id <id> (collect now)")

    if a.snap:
        snap = os.path.join(t, "snapshots", f"ads_{a.snap}.json")
        if not os.path.exists(snap):
            os.makedirs(os.path.dirname(snap), exist_ok=True); shutil.copy(os.path.join(t, "ads.json"), snap)
            print("snapshotted ads.json ->", snap)
        run(py, f"{here}/refresh_foreplay.py", t, a.pages, a.snap, a.now)
    else:
        if os.path.exists(os.path.join(t, "ads.json")):
            sys.exit("ads.json exists — pass --snap <date> to refresh instead of re-consolidating")
        run(py, f"{here}/consolidate_foreplay.py", t, a.pages, a.now)
    run(py, f"{here}/analyze_survival.py", os.path.join(t, "ads.json"))
    run(py, f"{here}/fetch_stills.py", t)
    run(py, f"{here}/compile_transcripts_fp.py", t)
    if os.path.exists(os.path.join(t, "build_report.py")):
        run(py, "build_report.py", cwd=t)
        run(py, f"{here}/validate_report.py", t)
    else:
        print("\nno build_report.py in target — copy one from a previous target and rewrite its prose")

if __name__ == "__main__":
    main()
