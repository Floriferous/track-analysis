"""Export dossier analyses as DAW-ready MIDI (part of the track-analysis skill): bass blueprint from deep.json,
drum groove from a light-pass window. Times are in beats at the track BPM, so
clips loop cleanly; fractional 16th positions (the feel) are preserved.

`--check` validates the drum lanes before writing and refuses to ship musically
nonsense (no note on the downbeat, bar-long holes, a sub row the dossier already
flagged as bass pollution). Checks print PASS/WARN/FAIL with the measured number;
any FAIL exits non-zero and writes nothing unless --allow-suspect is given.
`--check-mid` runs the same lane checks over an existing .mid instead of exporting.

Usage: python midi.py --deep <deep.json> [--dossier <dossier.json> --window 3m00s] --out <dir> [--check]
       python midi.py --check-mid <file.mid> [--deep <deep.json>]
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pretty_midi

GM = {"kick": 36, "hats": 42, "perc": 37}
BAND = {"kick": "sub", "hats": "high", "perc": "mid"}  # lane -> dossier grid-row prefix
MAX_OFF_MS = 40  # ingest's own on-grid window; hits past it are not this band's
VEL_FLOOR = 20


def bass_midi(deep, out):
    bpm = deep["bpm"]
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    inst = pretty_midi.Instrument(program=38, name="bass blueprint")  # synth bass 1
    b0 = deep["bass_notes"]["bars"][0]
    spb = 60.0 / bpm  # seconds per beat in the exported clip
    for n in deep["bass_notes"]["notes"]:
        start_beats = (n["bar"] - b0) * 4 + n["pos16"] / 4
        dur_beats = max(n["dur16"] / 4, 0.1)
        pitch = pretty_midi.note_name_to_number(n["note"].replace("♯", "#"))
        inst.notes.append(pretty_midi.Note(velocity=100, pitch=pitch,
                                           start=start_beats * spb, end=(start_beats + dur_beats) * spb))
    pm.instruments.append(inst)
    pm.write(str(out))
    return len(inst.notes)


def drum_lanes(dossier, window):
    """(lanes, kept, bars) for a window. lanes: {name: [(start_beats, velocity)]}, kept: {name: (n_kept, n_band)}."""
    bpm = dossier["bpm"]
    w = dossier["windows"][window]
    rows = {name: next(k for k in w["grids"] if k.startswith(p)) for name, p in BAND.items()}
    lanes, kept = {}, {}
    for name, band in rows.items():
        hits = w["grids"][band]
        on = [h for h in hits if abs(h["offset_ms"]) <= MAX_OFF_MS]
        # grid16/4 is the beat position; the offset is the micro-feel, in beats
        lanes[name] = sorted((h["grid16"] / 4 + h["offset_ms"] * bpm / 60000,
                              max(VEL_FLOOR, int(h["vel"] * 127))) for h in on)
        kept[name] = (len(on), len(hits))
    bars = max(1, round((w["t1"] - w["t0"]) * bpm / 240))
    return lanes, kept, bars


def drum_midi(dossier, window, out, zero=()):
    """Write the window's lanes; lanes named in `zero` are snapped to the 16th grid (C5)."""
    bpm = dossier["bpm"]
    spb = 60.0 / bpm
    lanes, _, _ = drum_lanes(dossier, window)
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    inst = pretty_midi.Instrument(program=0, is_drum=True, name=f"groove @{window}")
    for name, notes in lanes.items():
        for start, vel in notes:
            t = max(0.0, (round(start * 4) / 4 if name in zero else start) * spb)
            inst.notes.append(pretty_midi.Note(velocity=vel, pitch=GM[name], start=t, end=t + 0.08))
    pm.instruments.append(inst)
    pm.write(str(out))
    return len(inst.notes)


def mid_lanes(path):
    """(lanes, bpm, bars) read back from a .mid: drum tracks split by GM pitch, pitched tracks kept whole."""
    pm = pretty_midi.PrettyMIDI(str(path))
    bpm = float(pm.get_tempo_changes()[1][0])
    names = {v: k for k, v in GM.items()}
    lanes = {}
    for inst in pm.instruments:
        for n in inst.notes:
            key = names.get(n.pitch, f"pitch{n.pitch}") if inst.is_drum else (inst.name or "inst")
            lanes.setdefault(key, []).append((pm.time_to_tick(n.start) / pm.resolution, n.velocity))
    lanes = {k: sorted(v) for k, v in lanes.items()}
    last = max((v[-1][0] for v in lanes.values() if v), default=0.0)
    return lanes, bpm, max(1, round((last + 1) / 4))


def sub_grid_suspect(w):
    """ingest.py's failure-mode-2 rule, recomputed from stored offsets (an absent flag is unknown, not false)."""
    sd = {b: (len(on), float(np.std([h["offset_ms"] for h in on])))
          for b, hits in w["grids"].items()
          for on in [[h for h in hits if abs(h["offset_ms"]) < MAX_OFF_MS]] if on}
    sub = next((v for k, v in sd.items() if k.startswith("sub")), None)
    others = [s for k, (n, s) in sd.items() if not k.startswith("sub") and n >= 4]
    return bool(sub and sub[0] >= 6 and sub[1] >= 15 and others and np.median(others) <= 8)


def _dev_ms(st, bpm):
    """Signed deviation of each onset from its nearest 16th, in ms."""
    return (st - np.round(st * 4) / 4) * 60000.0 / bpm


def _modal_ioi(d):
    """Most common inter-onset interval, rounded to the 32nd; median if that degenerates."""
    if not len(d):
        return None
    m = Counter(round(float(x) / 0.125) * 0.125 for x in d).most_common(1)[0][0]
    return m or float(np.median(d))


def check_lanes(lanes, bpm, bars, w=None, kept=None, deep=None):
    """Run the checks. Returns (rows, zero) — rows are (code, scope, status, detail),
    zero is the lanes whose offsets C5 says are a cross-element artifact, not groove."""
    rows, zero, beats = [], [], int(round(bars * 4))
    kpb = None
    if deep and deep.get("kick", {}).get("n") and deep.get("t_end", 0) > deep.get("t_start", 0):
        kpb = deep["kick"]["n"] / ((deep["t_end"] - deep["t_start"]) * deep["bpm"] / 60)
    if w is not None:  # C12 suspect gate — the flag ingest.py already wrote, or the same rule rerun
        flag, src = w.get("sub_grid_suspect"), "stored"
        if flag is None:
            flag, src = sub_grid_suspect(w), "recomputed (flag absent)"
        rows.append(("C12", "window", "FAIL" if flag else "PASS", f"sub_grid_suspect={str(bool(flag)).lower()}, {src}"))
    for name, (k, n) in (kept or {}).items():  # C13 off-grid drop rate
        drop = 100.0 * (n - k) / n if n else 0.0
        rows.append(("C13", name, "FAIL" if drop > 25 else "PASS",
                     f"{drop:.1f}% of {n} band hits dropped by |offset|>{MAX_OFF_MS}ms ({n - k} of {n})"))
    for name, notes in lanes.items():
        st = np.array([s for s, _ in notes])
        vel = np.array([v for _, v in notes])
        per_bar = len(st) / bars
        if not len(st) or (name in ("kick", "hats") and per_bar < 2):  # C7 empty lane
            rows.append(("C7", name, "FAIL", f"{len(st)} notes over {bars} bars ({per_bar:.2f}/bar)"))
            continue
        rows.append(("C7", name, "PASS", f"{len(st)} notes over {bars} bars ({per_bar:.2f}/bar)"))
        d, dev = np.diff(st), _dev_ms(st, bpm)
        modal = _modal_ioi(d)
        # C1 downbeat presence — KICK ONLY. A one-beat modal IOI means "a note
        # every beat", not "a note ON the beat": an offbeat open-hat pattern is
        # exactly that and is perfectly musical, so demanding integer-beat
        # alignment of any non-kick lane is a false positive. On the kick it is
        # the incident itself (four-on-the-floor with nothing on beat 1).
        four = name == "kick" and ((modal is not None and abs(modal - 1) <= 0.05)
                                   or (kpb and abs(kpb - 1) <= 0.3))
        if four:
            miss = [b for b in range(beats) if np.min(np.abs(st - b)) > 0.06]
            why = f"modal IOI {modal:.3f}" if modal and abs(modal - 1) <= 0.05 else f"{kpb:.2f} kicks/beat in deep.json"
            rows.append(("C1", name, "FAIL" if miss else "PASS",
                         f"4-on-floor implied ({why}); {len(miss)}/{beats} beats with no note within 0.06 beat"
                         + (f", first at beat {miss[0]}" if miss else "")))
        else:
            phase = f"modal IOI {modal:.3f} beat" if modal else "one note, no IOI"
            rows.append(("C1", name, "n/a", f"not a 4-on-floor kick ({phase})"))
        if len(d):  # C2 IOI conformance
            mult = np.maximum(1, np.round(d / 0.25))
            pct = 100.0 * np.mean(np.abs(d - mult * 0.25) <= 0.05 * mult * 0.25)
            rows.append(("C2", name, "PASS" if pct >= 90 else "FAIL", f"{pct:.1f}% of {len(d)} IOIs within 5% of a 16th multiple"))
        if len(st) >= 8:  # C3 implausible gap
            gap = float(d.max())
            bad = gap > 2 * modal or gap > 4
            rows.append(("C3", name, "FAIL" if bad else "PASS",
                         f"largest gap {gap:.2f} beat (modal IOI {modal:.3f}, limits {2 * modal:.2f} / 4.00)"))
        sd, mean = float(np.std(dev)), float(np.mean(dev))
        rows.append(("C4", name, "FAIL" if sd >= 15 else "WARN" if sd >= 8 else "PASS",  # C4 deviation spread
                     f"deviation sd {sd:.1f}ms"))
        if abs(mean) > 15 and sd < 8:  # C5 systematic bias -> cross-element artifact, not groove
            zero.append(name)
            rows.append(("C5", name, "WARN", f"mean {mean:+.1f}ms at sd {sd:.1f}ms — cross-element artifact; offsets zeroed"))
        else:
            rows.append(("C5", name, "PASS", f"mean {mean:+.1f}ms at sd {sd:.1f}ms"))
        v_sd, top, floor = float(np.std(vel)), np.mean(vel >= 127), np.mean(vel <= VEL_FLOOR)
        # C9 velocity sanity. Pile-ups at the ceiling/floor are detector artifacts
        # (window-normalised vel, promoted near-silent hits) and block the write.
        # Flat velocity only WARNs: it is the signature of a hand-programmed lane,
        # which is a legitimate authoring choice, not nonsense.
        bad9 = top > 0.10 or floor > 0.25
        flat9 = v_sd == 0 and len(vel) > 8
        rows.append(("C9", name, "FAIL" if bad9 else "WARN" if flat9 else "PASS",
                     f"sd {v_sd:.1f}, {100 * top:.0f}% at 127, {100 * floor:.0f}% at the floor {VEL_FLOOR}"
                     + (" — flat velocity (hand-programmed?)" if flat9 else "")))
        if name == "kick":  # C16 kick-density cross-check
            got = len(st) / beats
            rel = (got - kpb) / kpb if kpb else None
            rows.append(("C16", name, "n/a" if rel is None else "FAIL" if abs(rel) > 0.30 else "PASS",
                         f"{got:.2f} kicks/beat, no --deep to compare against" if rel is None else
                         f"{got:.2f} kicks/beat vs {kpb:.2f} expected from deep.json ({100 * rel:+.0f}%)"))
    return sorted(rows, key=lambda r: (int(r[0][1:]), r[1])), zero


def report(rows, title):
    print(f"CHECK {title}")
    for code, scope, status, detail in rows:
        print(f"  {code:<4} {scope:<7} {status:<4}  {detail}")
    n_fail = sum(r[2] == "FAIL" for r in rows)
    n_warn = sum(r[2] == "WARN" for r in rows)
    print(f"  -> {n_fail} FAIL, {n_warn} WARN, {sum(r[2] == 'PASS' for r in rows)} PASS")
    return n_fail, n_warn


if __name__ == "__main__":
    import sys

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--deep", help="deep.json path (bass blueprint; also feeds the C16 kick-density check)")
    ap.add_argument("--dossier", help="light-pass dossier.json path (drum groove)")
    ap.add_argument("--window", help="window label in dossier, e.g. 3m00s")
    ap.add_argument("--out", default=".", help="output directory")
    ap.add_argument("--check", action="store_true", help="validate the drum lanes; write nothing if any check FAILs")
    ap.add_argument("--check-mid", help="validate an existing .mid and exit (no export); the checks are"
                                        " calibrated for drum lanes, read them accordingly on a pitched clip")
    ap.add_argument("--allow-suspect", action="store_true", help="report FAILs but export anyway")
    a = ap.parse_args()
    deep = json.loads(Path(a.deep).read_text()) if a.deep else None
    if a.check_mid:
        lanes, bpm, bars = mid_lanes(a.check_mid)
        rows, _ = check_lanes(lanes, bpm, bars, deep=deep)
        n_fail, _ = report(rows, f"{Path(a.check_mid).name} ({bpm:.1f} BPM, {bars} bars assumed)")
        sys.exit(1 if n_fail and not a.allow_suspect else 0)
    if not a.deep and not (a.dossier and a.window):
        ap.error("nothing to export: pass --deep and/or both --dossier and --window")
    if bool(a.dossier) != bool(a.window):
        ap.error("--dossier and --window go together")
    dossier = json.loads(Path(a.dossier).read_text()) if a.dossier else None
    zero = ()
    if a.check:
        if not dossier:
            ap.error("--check validates the drum lanes: pass --dossier and --window")
        lanes, kept, bars = drum_lanes(dossier, a.window)
        rows, zero = check_lanes(lanes, dossier["bpm"], bars, w=dossier["windows"][a.window], kept=kept, deep=deep)
        n_fail, _ = report(rows, f"{dossier['slug']} @{a.window} ({dossier['bpm']:.1f} BPM, {bars} bars)")
        if n_fail and not a.allow_suspect:
            print(f"  refusing to write: {n_fail} FAIL — fix the source window, pick another one,"
                  " or pass --allow-suspect if you know what is wrong with it")
            sys.exit(1)
        if n_fail:
            print("  --allow-suspect given: writing despite the failures above")
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    if deep:
        f = outdir / f"{deep['slug'][:40]}_bass.mid"
        print(f"{f.name}: {bass_midi(deep, f)} notes @ {deep['bpm']:.1f} BPM")
    if dossier:
        f = outdir / f"{dossier['slug'][:40]}_drums_{a.window}.mid"
        print(f"{f.name}: {drum_midi(dossier, a.window, f, zero)} hits @ {dossier['bpm']:.1f} BPM")
