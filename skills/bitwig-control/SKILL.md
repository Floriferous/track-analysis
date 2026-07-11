---
name: bitwig-control
description: Control Bitwig Studio from the command line over OSC (DrivenByMoss) — transport and tempo, creating clips and loading MIDI files into them, launching clips, playing notes, editing synth/device parameters, and browsing presets. Use when the user wants a groove or MIDI placed into Bitwig, wants Bitwig played/stopped/tempo-changed, wants a synth or device parameter tweaked, or wants analysis results from the track-analysis skill recreated or auditioned in Bitwig.
---

# Bitwig Control

Bitwig is driven over OSC through the DrivenByMoss extension: commands go to
Bitwig on port 8000, state feedback streams back on port 9000. Everything runs
through `scripts/bw.py` — one-shot CLI commands, no daemon. This pairs with the
`track-analysis` skill: analyze → export MIDI → inject into Bitwig → compare.

## One-time setup (once per machine)

1. `DrivenByMoss.bwextension` must be in `~/Documents/Bitwig Studio/Extensions/`
   (download: <https://www.mossgrabers.de/Software/Bitwig/Bitwig.html>, Bitwig 5.3+).
2. In Bitwig: **Dashboard → Settings → Controllers → + Add Controller →
   Utilities → Open Sound Control**, then activate it. This is a human step —
   ask the user to do it; there is no API to add a controller.
3. Defaults expected by `bw.py`: receive port **8000**, send host **127.0.0.1**,
   send port **9000**, value resolution **128**. Override with env vars
   `BITWIG_OSC_HOST/SEND_PORT/FEEDBACK_PORT/RESOLUTION` if the user changed them
   in the controller's settings.
4. Python side: `pip install python-osc` (any Python ≥3.9; the track-analysis
   venv works).

## Steps

1. **Verify the link first.** `python scripts/bw.py ping` — it listens for
   DrivenByMoss feedback and prints project/tempo/device state. Done when it
   prints `OK`. If it fails it prints the checklist; most common cause: the OSC
   controller isn't added/active in Bitwig, or Bitwig isn't running
   (`open -a "Bitwig Studio"`, then the user picks/creates a project).
2. **Read before you write.** `bw.py state /track` or `bw.py params` shows what
   the cursor actually points at — track names, selected device, current
   parameter page with names and display values. Never set a parameter you
   haven't listed; index 3 is a different knob on every page.
3. **Act** with the focused commands (`tempo`, `clip-create`, `clip-insert-file`,
   `clip-launch`, `param`, `note`, browser commands — `bw.py -h` lists all;
   address semantics in `references/osc-protocol.md`). Anything not wrapped:
   `bw.py raw /address args`.
4. **Verify the effect** — re-read state (`params`, `state /track`) or ask the
   user what they hear. OSC is fire-and-forget UDP; the feedback stream is the
   only confirmation a command landed.

## Recreating a groove (the track-analysis handoff)

```
bw.py tempo 125                                   # match the analyzed BPM
bw.py clip-insert-file 1 1 /abs/path/groove.mid   # into an EMPTY slot — creates + fills
bw.py clip-launch 1 1
```

- `insertFile` needs an **absolute path** and **REPLACES the slot's content**.
  An empty clip *name* does not mean an empty slot — unnamed clips have blank
  names; only `hasContent` tells the truth (a lesson from overwriting real
  project clips). `bw.py clip-insert-file` refuses non-empty slots unless
  `--force`. Prefer working in a scratch project or an empty scene, and confirm
  with the user before writing into a project that matters.
- `clip-create` before `insertFile` is an anti-pattern: a created clip has
  `hasContent 1`, so the guard refuses it. `clip-create` exists for making an
  empty clip to record or draw into.
- Clips take their name from the MIDI file's track name — name your
  pretty_midi instruments.
- **Hearing check**: while a clip or note plays, `/track/{n}/vu` in the
  feedback goes nonzero within ~100 ms. Playing clip + zero VU = missing
  instrument or broken routing.
- MIDI-file insertion preserves the exported micro-offsets and velocities
  exactly. `vkb_midi` notes do not (UDP timing) — use `note` for auditioning a
  sound, never for recording a groove. Notes broadcast to **every**
  record-armed/monitoring track: arm exactly one before playing.
- Drum grooves from `midi.py` land on General-MIDI-ish drum notes (kick 36,
  hats 42/46); route the clip to a drum machine/sampler accordingly, or ask the
  user what instrument the track holds.

## Editing a synth

The cursor device is **shared state with the human at the GUI** — their clicks
move it between your write and your readback (observed live: a run of param
writes silently landed elsewhere while the user was adding a device). Announce
device edits, pin the cursor when working (`raw /device/pinned 1`), and treat
readback as the write — `bw.py param` verifies and retries automatically.

1. Select the device (user clicks it, or walk the chain: `bw.py device +`,
   `bw.py state /device`).
2. `bw.py params` — lists the current page's 8 knobs with names and values;
   `bw.py page +`/`page 2` switches remote-control pages.
3. `bw.py param 3 0.5` — floats 0..1 scale to the configured resolution; raw
   ints pass through.
4. Presets/devices: `browser-preset` or `browser-device-after`, then
   `browser-filter`/`browser-result` to navigate (feedback shows the visible
   names), `browser-commit` or `browser-cancel`. Know its limits before
   committing to this route (all observed live):
   - **No search-by-name** — only stepping through filter items and results.
   - **Result feedback goes stale**: after changing a filter or tab, the
     `/browser/result/*` addresses may keep reporting the previous list even
     through a `/refresh`. Filter *selection* state updates reliably; result
     lists don't always.
   - **Category filters can hide the target**: the Drum Machine device is a
     container, so Category=Drums shows drum *presets* but not the device.
   - Verdict: fine for coarse moves (open, commit whatever the user selected,
     cancel); for picking a specific device or preset by name, ask the user to
     click it — seconds by hand, minutes of unreliable stepping over OSC.

## Trust boundaries & gotchas

- **Bank-relative indices**: track/clip/device numbers are positions in an
  8-wide bank window, not absolute project positions. `bw.py state /track`
  shows which tracks the window currently covers.
- **No error replies**: a wrong address or index is silently ignored. Absence
  of a state change in feedback is the only failure signal.
- **The cursor follows the user**: device commands hit whatever device is
  selected in the GUI unless pinned (`raw /device/pinned 1`). Confirm with
  `params` before setting values.
- **Value resolution must match**: `param` scaling assumes the DrivenByMoss
  "Value resolution" preference (default 128). If knobs move to wrong values,
  check that preference vs `BITWIG_OSC_RESOLUTION`.
- **The Grid and plugin-internal UIs are unreachable** over OSC — those need
  GUI automation or the user's hands.
- **Undo exists but is blind**: `bw.py undo`/`redo` send `/undo`//`/redo`, but
  the undo *history* is not visible over OSC, and not every OSC-triggered
  change is undoable (an OSC tempo change was observed not to revert via undo).
  After a mistake in a project that matters, prefer telling the user exactly
  what was changed, in order, and letting them drive Cmd+Z with eyes on the
  history.

## Files

- `scripts/bw.py` — the CLI; env-var config at the top.
- `references/osc-protocol.md` — curated OSC address reference (clips, device,
  browser, vkb_midi, feedback semantics).
- `references/verified-behaviors.md` — the experiment log: every claim tested
  live with readbacks, plus field rules and the untested frontier. Extend it
  the same way — one experiment, one readback, one entry — and consult it
  before assuming an address works.
