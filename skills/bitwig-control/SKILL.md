---
name: bitwig-control
description: Drive Bitwig Studio over OSC via DrivenByMoss. Use when the user wants a groove or MIDI file placed into Bitwig, clips or scenes launched, tempo or transport changed, a synth parameter tuned, a Bitwig device added, a sample auditioned in a clip, or track-analysis results recreated in the DAW.
---

# Bitwig Control

Everything goes through `scripts/bw.py` — one-shot CLI commands over OSC
(`bw.py -h` lists them; `bw.py raw /address args` reaches any address, see
`references/osc-protocol.md`). Two facts shape every move:

- Bitwig sends no error replies, so **the readback is the write**: a mutation
  exists once the feedback stream shows it, and not before. `param` and
  `clip-insert-file` read back automatically; after `raw`, re-read `state`
  yourself.
- The human at the GUI **shares the cockpit**: their clicks move the selection
  and the cursor device between your write and your readback, and Bitwig
  renames tracks after their devices. Trust indices + fresh reads, announce
  what you're about to touch, and pin the cursor for device work.

## Every session, before anything else

1. `bw.py ping` — done when it prints `OK` with the project name. On failure it
   prints its own checklist; a machine that never had the link needs
   `references/setup.md`.
2. Map the terrain: `bw.py state /track` — done when you can name every
   visible track, its type, and which slots have content. Indices are
   positions in an 8-wide **bank window** (`/track/bank/{+,-}` slides it), not
   absolute project positions — and an index past the window **crashes the
   OSC extension** (user must click Restart in Bitwig). `bw.py` refuses such
   indices; bounds-check any hand-rolled `raw` or script send yourself.
3. Match the stakes: experiments belong in a scratch project; in a project
   that matters, snapshot the current readback of anything you'll change and
   confirm destructive writes with the user first.

## Tasks

### Groove or MIDI file into a clip

```
bw.py tempo 125                                   # match the analyzed BPM
bw.py clip-insert-file 1 1 /abs/path/groove.mid   # empty slot: creates + fills
bw.py clip-launch 1 1
```

Done when the insert prints `hasContent = 1` — and, when it should be audible,
the hearing check passes. `insertFile` takes an absolute path, preserves the
file's micro-offsets and velocities exactly, and REPLACES slot content, so the
command refuses a non-empty slot (`--force` only for a replacement the user
asked for). Clips inherit the MIDI file's track name — name your pretty_midi
instruments. Drum exports land on GM-ish notes (kick 36, hats 42/46): the
target track needs a drum instrument, so check what it holds or ask.
`clip-create` is for a different job — an empty clip to record or draw into.

### Scenes and arrangement

A track's slot *column* holds variations; `raw /scene/{n}/launch` switches the
whole row, launch-quantized, and the previous row stops itself. Done when
`state` shows `isPlaying 1` on the intended row. Sketch an arrangement arc
(intro → build → drop → fill) as one scene per section, tracks in sync.
`raw /scene/add` appends an empty row when the grid runs out;
`raw /scene/create` captures the currently *playing* clips into a new scene —
snapshot a combination the user likes before changing it.

### Audition a sound

`bw.py note <ch> <note> <vel>` plays through **every** record-armed or
monitoring track — arm exactly one first. Timing rides on UDP, so grooves go
in as MIDI files; `note` is for hearing a patch.

**Hearing check** (works for any playing clip or note): `/track/{n}/vu` in the
feedback goes nonzero within ~100 ms of real sound. A playing clip with zero
VU means a missing instrument or broken routing.

### Tune a synth or device

Named device? Check the `bitwig-devices` skill first — its recipes carry
parameter maps, anchor values, and verified presets that beat rediscovery.

1. Get the cursor onto the device — user clicks it, or walk with
   `bw.py device +` — then `raw /device/pinned 1` to hold it against cockpit
   churn.
2. `bw.py params` — the current page's 8 knobs with names and display values;
   `bw.py page +` / `page 2` switches pages. Set only knobs you've just
   listed: index 3 is a different knob on every page.
3. `bw.py param 3 0.5` (floats 0..1 scale to the configured resolution) —
   done when it prints `[OK]` with the intended display value; `MISMATCH`
   means the cursor moved — re-run `params` and re-aim.
4. When the user is at the GUI, skip page hunting entirely:
   they click the knob, you write `raw /device/lastparam/value <int>` — it
   targets whatever parameter has GUI focus.

### Add a Bitwig device

The reliable flow is contextual: select an **empty instrument track**, then
`browser-device-after` — the browser opens pre-filtered to instruments, a
short list. `browser-result +` until the target reads `isSelected 1`, then
`browser-commit`. Done when `state /device` shows the target's name. For
anything beyond that flow — a specific preset by name, deep filter navigation
— hand it to the user: their two seconds beat minutes of blind stepping
(evidence in `references/verified-behaviors.md`).

### Use samples

`clip-insert-file` with a `.wav` into an **audio track's** empty slot makes a
playing audio clip — same guard, same hearing check, no instrument needed. The
user's sample library is fair game for clip work.

### The tweak loop (tune a sound by measurement)

You cannot hear; this loop is how you tweak anyway. One-time per project:
the print track's input must be the Master bus (human step, see setup
walk-through in `references/verified-behaviors.md` context). Then iterate:

```
bw.py param 3 0.6            # or lastparam via the user's click
python capture.py --project-dir <proj> --solo <track> --bars 1 --json
```

`capture.py` records the playing groove into a print-track slot, waits for
the WAV in the project's `recordings/` folder, returns hear.py metrics
(f0, harmonic ladder, band shares, level, `--pump` duck/shape) as JSON, and
frees the slot — ~7–9 s per iteration when the groove keeps playing between
calls. Launch the scene once at the start (`--scene N` on the first capture);
leave it playing. Done when the measured profile matches the target (a
reference stem's hear.py output is the natural target) or the user's ears
approve. State the target numbers before the first iteration — a loop
without a numeric target is just wiggling knobs.

Sidechain-specific physics (all learned calibrating a real one):
- **Solo kills the key**: soloing the destination track mutes the key-source
  track and the pump vanishes. To isolate the pumped signal, **mute the
  key-source track instead** — a key tapped inside a container (e.g. a Drum
  Machine pad chain) stays live under track mute.
- Key from the **kick pad's chain**, not the whole drum track, or hats
  trigger ducks on the offbeats.
- Measure pump on a band the pumped signal owns (`--pump-band 120,300` for a
  bass under a kick); in full-mix captures the floor includes the kick's own
  in-band energy, so isolated (muted-key) readings run deeper than mix ones.

### Recover from a mistake

Stop the sound first (`raw /clip/stopall`, `stop`), then narrate exactly what
changed, in order, and let the user drive Cmd+Z with eyes on the history.
Your failed commands are visible too — Bitwig's controller console prints
`Unknown OSC command:` / `Illegal parameter:` lines, worth checking when
debugging. `/project/save` exists: save only when the user asks.
`bw.py undo`/`redo` exist but fire blind — history is unreadable over OSC and
an OSC tempo change was observed not to revert — so they're for your own
just-made, just-verified edit, and narration is for everything else.

## Human hands required

One-time controller setup (`references/setup.md`) · adding VST/CLAP plugins
(invisible to the OSC browser — once the user adds one, `params`/`param` work
on it like any device) · loading kits or samples into container devices (a
fresh Drum Machine is silent until its pads are filled) · picking presets by
name · The Grid and plugin-internal UIs.

## Files

- `scripts/bw.py` — the CLI; env-var config at the top.
- `references/setup.md` — one-time machine setup; read when `ping` fails on a
  fresh machine.
- `references/osc-protocol.md` — address reference; read before composing any
  `raw` command. Its ground truth is the DrivenByMoss source at
  `opensrc/DrivenByMoss` (fetch instructions in the reference's header) —
  read the module class when the table falls short.
- `references/verified-behaviors.md` — the evidence log behind every rule
  here, plus the untested frontier; read before relying on an address or
  behavior no task above covers, and extend it the same way — one experiment,
  one readback, one entry.
