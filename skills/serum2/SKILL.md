---
name: serum2
description: Sound-design on Xfer Serum 2 inside Bitwig — driving it over MIDI CC (the only programmatic path), iterating timbre by measurement, and reading/writing Xfer's file formats. Use when a task names Serum — tweaking or building a patch, its MIDI maps or preset files, or a Serum parameter that won't respond.
---

# Serum 2

Serum 2 publishes **zero parameters to the host** (VST3 only, no CLAP) — so
unlike Diva there is nothing to enumerate and no write readback. The backbone
is MIDI CC into a learned map, and **the capture loop is the only proof a
value landed**: never verify by asking the human to watch, always by
measurement. Mechanics (OSC, capture/hear) come from `bitwig-control`; this
skill is the Serum-specific knowledge.

## Every session

1. Arm exactly the Serum track (`bw.py raw /track/{n}/recarm 1`).
2. Something audible to measure: launch a held-note clip, capture a baseline.
3. Drive knobs over the **IAC bus**: `scripts/cc.py {cc} {0-127} [...]` —
   roster below. (Not vkb_midi: its CC injection died silently 2026-07-20
   while notes kept working; notes still go over vkb_midi.)
4. Verify each move with a capture; quote band shares/RMS, not hope. On a
   fresh setup, run the 10-second arrival probe first (see Traps).

## The roster (bound + verified 2026-07-17)

Filter 1: **22** Cutoff · **23** Resonance · **24** Drive · **25** Mix
OSC A: **26** Level · **27** WT Pos · **28** Unison Detune · **29** Warp
**30** Sub Level · **31** Noise Level
Env 1: **85** Attack · **86** Decay · **87** Sustain · **89** Release
Macros 1–8: **14–21** (preset-wired — dead on Init, rich on factory presets)

Lives in `default.SerumMIDIMap`, which auto-loads on new instances, Init,
and every preset change — the roster survives preset hopping. Full table
with paramIDs and measured fingerprints: `references/control-surface.md`.

## Branches

- **Knob is on the roster** → send its CC, measure. Done when the measured
  profile matches the target.
- **Knob is not on the roster** → either the user clicks it once and you
  drive `bw.py lastparam --expect <name>` (ad-hoc), or extend the roster:
  add it to `scripts/learn_roster.py`, user runs the script (right-click →
  MIDI Learn per knob), user re-saves the default map, you re-decode it
  (`scripts/serumfile.py map`) and update the table. Prefer extending for
  anything you'll touch twice.
- **Preset change** → user picks in Serum's own browser (Bitwig's browser
  lists none). The default map re-asserts the roster afterwards; macros
  CC14–21 now do whatever the preset wired.
- **A CC does nothing** → in order: is the Serum track the armed one? Is the
  target module powered on (Sub/Noise/Filter have power buttons — a knob on
  a dead module binds fine and sounds like nothing)? Is it a macro on a
  patch that never wired it? Only then suspect the map — decode the file.
- **Map/preset files themselves** → `scripts/serumfile.py` decodes both;
  `references/file-format.md` has the container spec (writing = untested).

## Traps

- A silent null result usually means *unwired*, not *broken* — Init macros
  and dead modules were tonight's two hour-eaters.
- **Loading any preset wipes the instance's CC bindings** — reload the map
  (menu → Load MIDI Map) and re-verify before iterating. Verify with the
  save-back readback (Save MIDI Map → `serumfile.py map`), not by sweeping.
- **Presets carry `mpeEnabled`** — loading an MPE-enabled preset flips the
  whole instance into MPE mode (pitch bend becomes per-note, CC10 becomes
  expression; manual p314). Check the payload when MIDI behaves strangely.
- **CC transport can silently regress** (incident 2026-07-20: vkb_midi
  notes reached Serum, CCs did not — survived map reloads, MPE off, fresh
  instance, full Bitwig restart; root cause in DrivenByMoss/Bitwig never
  found). Resolution: **CCs ride a dedicated IAC bus** ("claude-cc" / IAC
  Driver Bus 2 → a Generic controller in Bitwig → armed track), fully
  bypassing the OSC extension — `scripts/cc.py`. The 10-second arrival
  probe remains the health check for any fresh setup: user right-clicks a
  knob → MIDI Learn, you send a CC — learn completing proves arrival;
  learn still waiting means fix transport first, nothing downstream is
  testable.
- **File-loaded map bindings may not drive the engine**: after menu-loading
  a map, its bindings appear in Serum's state (save-back and right-click
  badges confirm) yet mapped CCs were observed doing nothing, while
  *live-learned* bindings work immediately. Until resolved: after any
  session/preset reset, re-learn the roster live (`scripts/learn_roster.py`,
  ~1 min) and treat the default-map file as backup/documentation, then
  verify one audible knob by capture before iterating.
- CC has no feedback anywhere (no OSC echo, no lastparam witness): a CC
  experiment with no measurement attached is not an experiment.
- `lastparam` focus follows every GUI click including power buttons —
  `--expect` or you may toggle a filter off.
- Keep Serum's Global pref "Load MIDI Map from Presets" **off** — it is what
  lets `default.SerumMIDIMap` re-assert on preset loads.
- A running instance does not re-read an edited map file — menu → Load MIDI
  Map, or any preset load.

## Files

- `references/control-surface.md` — layers, roster + paramIDs, map-loading
  semantics, why-no-enumeration evidence. Start here every session.
- `references/file-format.md` — XferJson container spec (maps + presets).
- `references/patches.md` — banked patch recipes (roster CC states +
  measured profiles).
- `references/Serum 2 User Guide.pdf` — official manual (MIDI: p26–27,
  macros: p206–208, prefs: p313+).
- `scripts/learn_roster.py` — self-paced MIDI-Learn binding session.
- `scripts/serumfile.py` — decode/inspect Xfer container files.
