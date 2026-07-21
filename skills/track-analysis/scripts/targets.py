"""Emit a per-element NUMERIC TARGET SHEET for a reference track.

The recreate-a-record loop is: measure the reference -> get numbers -> build
in the DAW -> capture -> converge. This script is the "get numbers" half, and
it exists because assembling that sheet by hand invites two silent errors that
have both actually happened:

  1. UNIT COLLISION. track-analysis and hear.py use the SAME band names for
     DIFFERENT frequencies (deep/ingest: bass=120-350, hear: bass=60-120; only
     `high` agrees). Comparing a deep.json band against a hear.py band under
     the matching key silently compares two different parts of the spectrum.
  2. CONVENTION COLLISION. deep.py's pump duck normalises by the curve's max;
     hear.py normalises by the p90 of the beat excluding its first 12%. The
     same curve reads 74.0% and 62.9%. Chasing the deep.py number with a
     hear.py measurement over-ducks by ~11 points.

So every number here is emitted in **hear.py units**, measured by hear.py
itself wherever possible, because hear.py is what measures the DAW side. A
target you cannot measure the same way on both sides is not a target.

Usage:
  python targets.py --deep <deep-slice-dir> [--dossier <dossier.json>] [--json]

<deep-slice-dir> is a deep.py output folder: it holds deep.json and the four
cached stem WAVs, which is everything the per-element rows need.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

# Deliberate cross-skill dependency: the whole point is to emit targets in the
# units the DAW side will be measured in, and hear.py IS that measurement. It
# must be the same code, not a reimplementation, or the two drift apart and the
# comparison silently stops meaning anything.
HEAR = Path(__file__).resolve().parents[2] / "bitwig-control" / "scripts" / "hear.py"


def hear(wav, **flags):
    """Run hear.py --json on a wav. Returns {} if it has nothing to say."""
    cmd = [sys.executable, str(HEAR), str(wav), "--json"]
    for k, v in flags.items():
        cmd += [f"--{k.replace('_', '-')}"] + ([] if v is True else [str(v)])
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0 or not p.stdout.strip():
        return {"error": (p.stderr or p.stdout).strip()[:200]}
    return json.loads(p.stdout)


def duck_in_hear_units(curve):
    """deep.py stores the folded beat curve normalised to its own max, and
    reports duck = 100*(1-min). hear.py instead references the p90 of the
    beat excluding its first 12% (the kick attack), so the SAME curve reads
    lower. Convert, or the DAW will be tuned to a target it can never read."""
    c = np.asarray(curve, dtype=float)
    ref = np.percentile(c[len(c) * 12 // 100:], 90)
    return 100 * max(0.0, 1 - c.min() / ref)


def band_row(label, h, keys=("sub", "bass", "low-mid", "mid", "high-mid", "high")):
    b = h.get("bands", {})
    return [label] + [f"{b[k]:.1f}" if k in b else "-" for k in keys]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deep", required=True, help="a deep.py output folder (deep.json + stems)")
    ap.add_argument("--dossier", default=None, help="dossier.json, for whole-track loudness/key")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not HEAR.exists():
        raise SystemExit(
            f"cannot find hear.py at {HEAR}\n"
            "targets.py needs the bitwig-control skill sitting beside this one, because "
            "it emits targets by running the same measurement the DAW side uses. Copy "
            "bitwig-control alongside track-analysis, or run this from the repo.")

    ddir = Path(args.deep)
    deep = json.loads((ddir / "deep.json").read_text())
    slug = deep["slug"]
    stems = {s: ddir / f"{slug}_{s}.wav" for s in ("drums", "bass", "other")}
    missing = [s for s, p in stems.items() if not p.exists()]
    if missing:
        raise SystemExit(f"missing stems {missing} in {ddir} — rerun deep.py to cache them")

    t = {"slug": slug, "bpm": deep["bpm"],
         "slice": [deep["t_start"], deep["t_end"]],
         "units": "hear.py bands (sub 25-60, bass 60-120, low-mid 120-350, "
                  "mid 350-2k, high-mid 2k-6k, high 6k-16k); shares are % of "
                  "total spectral power; width is % side"}

    # --- per-element spectral targets, measured by the SAME tool as the DAW side
    for name, wav in stems.items():
        h = hear(wav, width=True)
        t[name] = {"bands": h.get("bands"), "width_side_pct": h.get("width_side_pct"),
                   "rms_dbfs": h.get("rms_dbfs"), "f0_hz": h.get("f0_hz"),
                   "f0_note": h.get("f0_note"),
                   "peaks": [{k: p[k] for k in ("hz", "rel_db", "harmonic")}
                             for p in h.get("peaks", [])[:5]]}

    # --- structural targets that only the deep pass knows
    if "kick" in deep:
        k = deep["kick"]
        t["kick_anatomy"] = {"f0_start_hz": k["f0_start_hz"], "f0_end_hz": k["f0_end_hz"],
                             "sub_decay_ms": k["decay_ms"],
                             "note": "decay_ms null = sustained (no -20dB drop in the "
                                     "window). hear.py cannot measure decay — verify by ear."}
    if "pump" in deep:
        t["pump"] = {"duck_pct": round(duck_in_hear_units(deep["pump"]["curve"]), 1),
                     "min_at_beat_pct": deep["pump"]["min_at_beat_pct"],
                     "measure_with": "capture.py --pump --pump-band 300,6000",
                     "note": f"converted from deep.py's {deep['pump']['duck_pct']:.1f}% "
                             f"(max-referenced) into hear.py's p90 convention. "
                             f"min_at is NOISY — judge convergence on depth."}
    if deep.get("bass_notes", {}).get("notes"):
        n = deep["bass_notes"]["notes"]
        t["bass_notes"] = {"n": len(n), "pitches": sorted({x["note"] for x in n}),
                           "pos16": [x["pos16"] for x in n[:8]],
                           "mean_dur16": round(float(np.mean([x["dur16"] for x in n])), 2)}
    if args.dossier:
        d = json.loads(Path(args.dossier).read_text())
        t["reference_master"] = {"key": d.get("key"), "loudness": d.get("loudness"),
                                 "note": "whole-file and MASTERED — do not target LUFS "
                                         "from a pre-master DAW bus; crest is the fairer one."}

    if args.json:
        print(json.dumps(t, indent=1))
        return

    print(f"TARGETS: {slug}  {deep['t_start']:.0f}-{deep['t_end']:.0f}s  {deep['bpm']:.1f} BPM")
    print(f"units: {t['units']}\n")
    hdr = ["element", "sub", "bass", "lo-mid", "mid", "hi-mid", "high"]
    print(f"{hdr[0]:<10}" + "".join(f"{h:>9}" for h in hdr[1:]) + "   (% band energy)")
    for name in ("drums", "bass", "other"):
        r = band_row(name, t[name])
        print(f"{r[0]:<10}" + "".join(f"{v:>9}" for v in r[1:]))
    print()
    print(f"{'element':<10}" + "".join(f"{h:>9}" for h in hdr[1:]) + "   (% side / width)")
    for name in ("drums", "bass", "other"):
        w = t[name].get("width_side_pct") or {}
        cells = [f"{w[k]:.1f}" if k in w else "-" for k in hdr[1:]]
        print(f"{name:<10}" + "".join(f"{v:>9}" for v in cells))
    print()
    for name in ("drums", "bass", "other"):
        e = t[name]
        if e.get("f0_hz"):
            ladder = "  ".join(f"{p['hz']:.0f}Hz {p['rel_db']:+.1f}{p['harmonic']}"
                               for p in e["peaks"])
            print(f"{name:<10} f0 {e['f0_hz']:.1f} Hz ({e['f0_note']})  rms {e['rms_dbfs']:.1f} dBFS")
            print(f"{'':<10} ladder: {ladder}")
    if "kick_anatomy" in t:
        k = t["kick_anatomy"]
        print(f"\nkick       f0 glide {k['f0_start_hz']:.0f} -> {k['f0_end_hz']:.0f} Hz, "
              f"sub decay {k['sub_decay_ms'] or 'sustained'}")
    if "pump" in t:
        p = t["pump"]
        print(f"pump       duck {p['duck_pct']:.0f}% (hear.py units), min at "
              f"{p['min_at_beat_pct']:.0f}% of beat")
        print(f"           {p['note']}")
        print(f"           measure with: {p['measure_with']}")
    if "bass_notes" in t:
        b = t["bass_notes"]
        print(f"bass line  {b['n']} notes, pitches {b['pitches']}, "
              f"mean length {b['mean_dur16']} 16ths")
    print("\nEvery row above is measurable on the DAW side with the same tool:")
    print("  capture.py --print-track-name PRINT --bars 4 --width   (solo the element)")


if __name__ == "__main__":
    main()
