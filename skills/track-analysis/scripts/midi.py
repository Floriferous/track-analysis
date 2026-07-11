"""Export dossier analyses as DAW-ready MIDI (part of the track-analysis skill): bass blueprint from deep.json,
drum groove from a light-pass window. Times are in beats at the track BPM, so
clips loop cleanly; fractional 16th positions (the feel) are preserved.

Usage: python midi.py --deep <deep.json> [--dossier <dossier.json> --window 3m00s] --out <dir>
"""
import argparse
import json
from pathlib import Path

import pretty_midi

GM = {"kick": 36, "hats": 42, "perc": 37}


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


def drum_midi(dossier, window, out):
    bpm = dossier["bpm"]
    w = dossier["windows"][window]
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    inst = pretty_midi.Instrument(program=0, is_drum=True, name=f"groove @{window}")
    spb = 60.0 / bpm
    sixteenth = spb / 4
    rows = {"kick": next(k for k in w["grids"] if k.startswith("sub")),
            "hats": next(k for k in w["grids"] if k.startswith("high")),
            "perc": next(k for k in w["grids"] if k.startswith("mid"))}
    n = 0
    for name, band in rows.items():
        for h in w["grids"][band]:
            if abs(h["offset_ms"]) > 40:
                continue
            start = h["grid16"] * sixteenth + h["offset_ms"] / 1000  # keep the micro-feel
            inst.notes.append(pretty_midi.Note(velocity=max(20, int(h["vel"] * 127)),
                                               pitch=GM[name], start=max(0, start), end=max(0, start) + 0.08))
            n += 1
    pm.instruments.append(inst)
    pm.write(str(out))
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--deep", help="deep.json path (bass blueprint)")
    ap.add_argument("--dossier", help="light-pass dossier.json path (drum groove)")
    ap.add_argument("--window", help="window label in dossier, e.g. 3m00s")
    ap.add_argument("--out", default=".", help="output directory")
    a = ap.parse_args()
    if not a.deep and not (a.dossier and a.window):
        ap.error("nothing to export: pass --deep and/or both --dossier and --window")
    if bool(a.dossier) != bool(a.window):
        ap.error("--dossier and --window go together")
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    if a.deep:
        deep = json.loads(Path(a.deep).read_text())
        f = outdir / f"{deep['slug'][:40]}_bass.mid"
        print(f"{f.name}: {bass_midi(deep, f)} notes @ {deep['bpm']:.1f} BPM")
    if a.dossier and a.window:
        dossier = json.loads(Path(a.dossier).read_text())
        f = outdir / f"{dossier['slug'][:40]}_drums_{a.window}.mid"
        print(f"{f.name}: {drum_midi(dossier, a.window, f)} hits @ {dossier['bpm']:.1f} BPM")
