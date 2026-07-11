"""Diff two deep.json dossiers: the numbers a producer would A/B between
a work-in-progress and a reference (or two references). Part of the track-analysis skill;
field meanings: ../references/dossier-format.md

Usage: python compare.py a/deep.json b/deep.json
"""
import json
import sys

import numpy as np


def load(p):
    return json.loads(open(p).read())


def row(label, va, vb, flag=""):
    print(f"{label:<26} {va:<28} {vb:<28}{flag}")


def kick_desc(d):
    k = d.get("kick")
    if not k:
        return "n/a", "n/a"
    glide = f"{k['f0_start_hz']:.0f}->{k['f0_end_hz']:.0f}Hz"
    decay = f"{k['decay_ms']:.0f}ms" if k.get("decay_ms") else "sustained"
    return glide, decay


def bass_stats(d):
    notes = d["bass_notes"]["notes"]
    if not notes:
        return "none", "-", "-"
    b0, b1 = d["bass_notes"]["bars"]
    per_bar = len(notes) / max(1, b1 - b0)
    durs = [n["dur16"] for n in notes]
    on_kick = sum(1 for n in notes if round(n["pos16"]) % 4 == 0) / len(notes)
    pitches = "/".join(sorted({n["note"] for n in notes}))
    return (f"{per_bar:.1f}/bar, dur {np.mean(durs):.1f}+-{np.std(durs):.1f} 16ths",
            f"{100 * on_kick:.0f}% on kick 16ths", pitches)


a, b = load(sys.argv[1]), load(sys.argv[2])
row("", a["slug"][:26], b["slug"][:26])
row("bpm", f"{a['bpm']:.1f}", f"{b['bpm']:.1f}")
ga, da = kick_desc(a)
gb, db = kick_desc(b)
row("kick f0 glide", ga, gb)
row("kick sub decay", da, db)
row("sidechain duck", f"{a['pump']['duck_pct']:.0f}%", f"{b['pump']['duck_pct']:.0f}%")
def corr(x, y):
    x, y = np.asarray(x), np.asarray(y)
    if x.std() < 1e-9 or y.std() < 1e-9:  # constant vector (e.g. no hats detected)
        return None
    return float(np.corrcoef(x, y)[0, 1])


pump_r = corr(a["pump"]["curve"], b["pump"]["curve"])
hat_r = corr(a["hat_contour"]["vel"], b["hat_contour"]["vel"])
row("pump shape correlation", f"{pump_r:.2f}" if pump_r is not None else "n/a", "")
if hat_r is None:
    row("hat contour correlation", "n/a", "(no hats detected in one slice)")
else:
    row("hat contour correlation", f"{hat_r:.2f}", f"(accent skeletons {'match' if hat_r > 0.7 else 'differ'})")
for band, wa in a["stereo_width_side_share"].items():
    wb = b["stereo_width_side_share"][band]
    flag = "  <-- differs" if abs(wa - wb) > 0.12 else ""
    row(f"width {band}", f"{100 * wa:.0f}%", f"{100 * wb:.0f}%", flag)
sa, sb = bass_stats(a), bass_stats(b)
row("bass density/duration", sa[0], sb[0])
row("bass on-kick share", sa[1], sb[1])
row("bass pitches", sa[2], sb[2])
