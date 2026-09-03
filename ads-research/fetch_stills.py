#!/usr/bin/env python3
"""Get one still per featured ad, for the report cards.

Foreplay puts the still in different fields by format — `thumbnail` for video,
`image` for image ads, inside `cards` for carousel/DCO — and sometimes ships a
video with no still at all, in which case a frame is decoded with PyAV (the
bundled ffmpeg has no H.264). Featured = anything the report will card: live
ads past 60 days, every ad on a featured funnel, and anything new or dead since
the last snapshot.
"""
import json, os, sys, subprocess, importlib.util, concurrent.futures as cf

def still(a):
    if a.get("thumbnail"): return a["thumbnail"]
    if a.get("image"): return a["image"]
    for c in a.get("cards") or []:
        for k in ("thumbnail", "image"):
            if isinstance(c, dict) and c.get(k): return c[k]

def video(a):
    if a.get("video"): return a["video"]
    for c in a.get("cards") or []:
        if isinstance(c, dict) and c.get("video"): return c["video"]

def featured_funnels(target):
    p = os.path.join(target, "taxonomy.py")
    if not os.path.exists(p): return ()
    s = importlib.util.spec_from_file_location("t", p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return getattr(m, "FEATURED_FUNNELS", ())

def main(target):
    ads = json.load(open(os.path.join(target, "ads.json")))
    feat_f = featured_funnels(target)
    big, small = os.path.join(target, "thumbs"), os.path.join(target, "thumbs_small")
    os.makedirs(big, exist_ok=True); os.makedirs(small, exist_ok=True)
    feat = [a for a in ads if a.get("funnel") in feat_f or a.get("new_since") or a.get("died_between")
            or (a.get("live") is True and a.get("days_running", 0) >= 60)]
    todo_img, todo_vid, none = [], [], []
    for a in feat:
        out = f"{big}/{a['id']}.jpg"
        if os.path.exists(out) and os.path.getsize(out) > 1000: continue
        (todo_img if still(a) else todo_vid if video(a) else none).append(a)

    def get(a):
        out = f"{big}/{a['id']}.jpg"
        subprocess.run(["curl", "-sS", "--max-time", "40", "-o", out, still(a)])
        return os.path.exists(out) and os.path.getsize(out) > 1000
    with cf.ThreadPoolExecutor(8) as ex: ok = sum(ex.map(get, todo_img))

    fok = 0
    if todo_vid:
        import av
        for a in todo_vid:
            mp4 = f"/tmp/{a['id']}.mp4"
            subprocess.run(["curl", "-sS", "--max-time", "90", "-o", mp4, video(a)])
            try:
                c = av.open(mp4)
                for fr in c.decode(c.streams.video[0]):
                    fr.to_image().save(f"{big}/{a['id']}.jpg", "JPEG", quality=85); fok += 1; break
                c.close()
            except Exception as e:
                print("frame failed", a["id"], e, file=sys.stderr)
            finally:
                if os.path.exists(mp4): os.remove(mp4)

    from PIL import Image
    n = 0
    for a in feat:
        p, out = f"{big}/{a['id']}.jpg", f"{small}/{a['id']}.jpg"
        if os.path.exists(p) and not os.path.exists(out):
            im = Image.open(p).convert("RGB"); im.thumbnail((300, 300), Image.LANCZOS)
            im.save(out, "JPEG", quality=62, optimize=True); n += 1
    print(f"stills: featured={len(feat)} fetched={ok}/{len(todo_img)} frame-grabbed={fok}/{len(todo_vid)} "
          f"no-media={len(none)} downscaled={n}")
    for a in none: print("  no media:", a["id"], a.get("display_format"), a.get("funnel"), file=sys.stderr)

if __name__ == "__main__":
    main(sys.argv[1])
