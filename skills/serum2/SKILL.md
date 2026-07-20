---
name: serum2
description: Sound-design on Xfer Serum 2 inside Bitwig — driving it over MIDI CC (the only programmatic path), iterating timbre by measurement, and reading/writing Xfer's file formats. Use when a task names Serum — tweaking or building a patch, its MIDI maps or preset files, or a Serum parameter that won't respond.
---

# Serum 2

Serum 2 publishes **no usable synthesis parameters to the host** (VST3
only, no CLAP; a few globals like Main Vol sit in Bitwig's param list but
remote pages come up empty) — so unlike Diva there is nothing to enumerate
and no write readback. The backbone
is MIDI CC into a learned map, and **the capture loop is the only proof a
value landed**: never verify by asking the human to watch, always by
measurement. Mechanics (OSC, capture/hear) come from `bitwig-control`; this
skill is the Serum-specific knowledge.

## Every session

1. Arm exactly the Serum track (`bw.py raw /track/{n}/recarm 1`).
2. Something audible to measure: launch a held-note clip, capture a baseline.
3. Drive knobs over the **IAC bus**: `scripts/cc.py {cc} {0-127} [...]` —
   roster below. vkb_midi is notes-only (see the transport trap).
4. Verify each move with a capture; quote band shares/RMS, not hope. On a
   fresh setup, run the 10-second arrival probe first (see Traps).

## The roster (bound + verified 2026-07-17)

Filter 1: **22** Cutoff · **23** Resonance · **24** Drive · **25** Mix
OSC A: **26** Level · **27** WT Pos · **28** Unison Detune · **29** Warp
**30** Sub Level · **31** Noise Level
Env 1: **85** Attack · **86** Decay · **87** Sustain · **89** Release
Macros 1–8: **14–21** (preset-wired — dead on Init, rich on factory presets)

Live-learned bindings drive the engine and persist with the DAW session;
`default.SerumMIDIMap` documents the roster and seeds new instances, but a
*file-loaded* binding is not proven to reach the engine (see the binding
lifecycle trap) — after any preset change or Init, re-learn live and verify
one audible knob by capture before iterating. Full table with paramIDs and
measured fingerprints: `references/control-surface.md`.

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
  lists none). Preset loads wipe live bindings — re-learn and probe before
  iterating (binding lifecycle trap); macros CC14–21 now do whatever the
  preset wired.
- **A CC does nothing** → in order: is the Serum track the armed one? Is the
  target module powered on (Sub/Noise/Filter have power buttons — a knob on
  a dead module binds fine and sounds like nothing)? Is it a macro on a
  patch that never wired it? Only then suspect the map — decode the file.
- **Map/preset files themselves** → `scripts/serumfile.py` reads AND writes
  both (proven); `references/file-format.md` has the container spec.

## Traps

- A silent null result usually means *unwired*, not *broken* — Init macros
  and dead modules were tonight's two hour-eaters.
- **Binding lifecycle**: *live-learned* bindings drive the engine and
  persist with the DAW session; **loading any preset wipes them**; loading
  a map *file* (menu, or the default-map auto-load) restores Serum's
  binding *state* — visible in right-click badges and the save-back
  readback (Save MIDI Map → `serumfile.py map`) — but was observed **not
  driving the engine**. So after any preset change, Init, or session
  restore: re-learn live (`scripts/learn_roster.py`, ~1 min), then verify
  one audible knob by capture. Keep the Global pref "Load MIDI Map from
  Presets" **off** (or presets bring their own maps); an edited map file is
  never re-read by a running instance on its own.
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
- CC has no feedback anywhere (no OSC echo, no lastparam witness): a CC
  experiment with no measurement attached is not an experiment.
- `lastparam` focus follows every GUI click including power buttons —
  `--expect` or you may toggle a filter off.

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
