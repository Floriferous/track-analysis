# Serum 2 ↔ Bitwig: the controllable surface

Everything here was live-verified 2026-07-17 (Serum 2 **2.1.5 VST3**, Bitwig
5.3.13, DrivenByMoss 26.6.2) unless marked otherwise. Mechanics (OSC sends,
capture loop) come from `bitwig-control`.

## Why Serum 2 is not Diva

- **Serum 2 publishes zero static parameters to the host.** `bw.py pages` /
  `params` on the cursor device return nothing — no pages, no params, and a
  GUI-touched param does *not* persist into the bank afterwards. This is
  Xfer's deliberate design (params are dynamic; their forum's answer for
  automation is per-knob right-click → Automate). The Diva-style
  enumerate-and-write workflow is impossible.
- **No CLAP build exists** (VST3/AU/AAX only; the 2.1.5 installer offers no
  format choice). Verified in the project file: `strings *.bwproject` shows a
  VST3 class ID for Serum 2, and Diva-style CLAP string IDs are absent.
- Consequence: **the control backbone is MIDI CC**, delivered over
  `/vkb_midi/1/cc/{cc} {0-127}` to the record-armed track. CC has **no
  feedback of any kind** — no OSC readback, no `lastparam` witness. The
  capture loop measurement is the *only* verification that a value landed.

## Control layers

1. **Roster CCs 22–31, 85–89** — preset-independent knob bindings (table
   below), stored in `default.SerumMIDIMap`. The workhorse.
2. **Macros CC 14–21** — Macro knobs 1–8. Only audible when the *preset*
   assigns macro destinations; **unwired on the Init patch** (a macro sweep
   there is silently dead — that is not a broken chain).
3. **`bw.py lastparam`** — drives the last GUI-touched param (user clicks the
   knob, agent writes). Focus follows *every* click, including power buttons;
   always pass `--expect <name>`. Ad-hoc use only.
4. **File layer** — `.SerumMIDIMap`/`.SerumPreset` decode fully
   (`scripts/serumfile.py`, `references/file-format.md`); writing them back
   is the untested frontier.

## The roster (CC ↔ knob ↔ paramID)

Single source of truth: `scripts/learn_roster.py` (procedure) and the decoded
`default.SerumMIDIMap` (ground truth on disk). Snapshot as bound and
byte-verified 2026-07-17:

| CC | knob | paramID | verified fingerprint (vs baseline) |
|---|---|---|---|
| 22 | Filter 1 Cutoff | 2000003 | RMS −52→−32 dBFS, H2–H8 appear |
| 23 | Filter 1 Resonance | 2000004 | high-mid share 0.7→35.2 |
| 24 | Filter 1 Drive | 2000005 | RMS −30.8→−12.9 |
| 25 | Filter 1 Mix | 2000001 | map-verified |
| 26 | OSC A Level | 1000001 | map-verified |
| 27 | OSC A WT Position | 1000039 | map-verified |
| 28 | OSC A Unison Detune | 1000026 | map-verified (inaudible at unison=1) |
| 29 | OSC A Warp amount | 1000033 | map-verified |
| 30 | Sub Level | 1004001 | sub share 61→93.5 |
| 31 | Noise Level | 1003001 | high share 0.0→13.5 |
| 85 | Env 1 Attack | 3000000 | map-verified |
| 86 | Env 1 Decay | 3000002 | map-verified |
| 87 | Env 1 Sustain | 3000003 | RMS −5.2 dB on held note |
| 89 | Env 1 Release | 3000004 | map-verified |

"map-verified" = binding read back from the map file bytes; not yet
separately measured. CC values map linearly onto the knob's full range
(7-bit: 128 steps — fine for iteration, polish by hand/file if ever needed).

**paramID scheme (inferred from the 22 verified IDs, unverified beyond
them):** `blockBase + 1000·instance + offset` — oscillators 1,00X,0YY
(A=1000, noise=1003, sub=1004; level offset 1), filter 2,000,0YY, envelopes
3,00X,0YY (Env1 A/D/S/R = 0/2/3/4 — 1 is likely Hold), macros 7,00X,000.
Extrapolations (OSC B level = 1001001, Env 2 attack = 3001000, …) are
plausible arithmetic, but each one must be proven by writing a map and
measuring before it enters this table.

## Map loading semantics (manual p26–27, live-confirmed)

- MIDI Learn assignments live in the *running instance* and save with the
  DAW session and with presets.
- `default.SerumMIDIMap` in `Serum 2 Presets/System/MIDI CC Maps/`
  auto-loads for **new instances**, on **Init Preset**, and on **every
  preset selection** — the last one only because the Global preference
  **"Load MIDI Map from Presets" is false** (checked in
  `~/Library/Preferences/Serum2Prefs.json`; keep it false, it is what makes
  the roster survive preset changes).
- A **running** instance does *not* re-read the default file when it changes
  on disk — use Serum menu → Load MIDI Map, or rely on the next preset load.

## Bitwig-side facts

- Bitwig's OSC browser lists no Serum presets (unlike Diva) — the user picks
  presets in Serum's own browser.
- vkb_midi (notes *and* CCs) reaches record-armed / monitoring tracks only —
  arm exactly the Serum track first.
- Init patch sounds at written pitch (no octave surprise; contrast Diva 3EE).
- Ready-made maps online are controller-vendor files (Novation's Serum 2 map
  is 549 bytes ≈ macros + filter pots). No full community map exists — 128
  CCs vs thousands of params; a custom roster *is* the state of the art.
