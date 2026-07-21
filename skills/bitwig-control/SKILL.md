---
name: bitwig-control
description: Drive Bitwig Studio over OSC via DrivenByMoss. Use when the user wants a groove or MIDI file placed into Bitwig, clips or scenes launched, tempo or transport changed, a synth parameter tuned, a Bitwig device added, a sample auditioned in a clip, or track-analysis results recreated in the DAW.
---

# Bitwig Control

Everything goes through `scripts/bw.py` — one-shot CLI commands over OSC
(`bw.py -h` lists them; `bw.py raw /address args` reaches any address, see
`references/osc-protocol.md`). Three facts shape every move:

- Bitwig sends no error replies, so **the readback is the write**: a mutation
  exists once the feedback stream shows it, and not before. `param` and
  `clip-insert-file` read back automatically; after `raw`, re-read `state`
  yourself. Two silent-failure modes make this load-bearing rather than
  pedantic: a **cold** continuous write is swallowed whole, and a `page`
  switch can miss so a `param` lands on the wrong knob.
- **Cold writes are primed for you — but only through `bw.py`.** A numeric
  write to a continuous parameter (`/track/{n}/volume`,
  `/device/layer/{n}/pan`, `/eq/freq/{n}`, …) is silently swallowed unless
  that address was written recently; `bw.py` now detects those addresses and
  double-sends automatically (`send()`/`is_continuous()`), printing
  `(primed)`. Discrete writes land cold and are never primed — priming
  `/clip/launch` would fire it twice, `/device/bypass` would toggle back,
  `/stop` would also rewind. If you send OSC by any other route, you own the
  priming. Mechanism, the allowlist, and raw↔display scales:
  `references/verified-behaviors.md`.
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
instruments. Drum exports land on GM-ish notes (kick 36, hats 42/46), but
**the user's kit is not GM until you have probed it** — one clip per
candidate note, relaunch, capture, compare rms (silent reads −240 dBFS).
A kit this session had only pads 37 and 42 loaded with 42 as the *open*
hat, so a GM-shaped clip left every offbeat silent and read as "thin"
rather than "broken". Probing costs ~10 captures; assuming costs an hour.
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
   `bw.py page <Name>` switches by *name* but **can silently fail** (`page Qs`
   on EQ+ stayed on Freqs), and a switch needs ~1.5-2 s to settle, so
   **`page`, sleep, `params`, and check the printed page header before any
   write** — a write issued into that window lands on the old page's knob at
   that index. `/device/page/{n}` by index is the fallback that worked.
   Set only knobs you've just listed: index 3 is a different knob on every
   page. And `bw.py pages` (JSON) over-reports: it inventories the panel, not
   the 8 live slots, so a param it lists may not exist on the page at all.
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

You cannot hear; this loop is how you tweak anyway — **the capture is the
readback**: a sound change exists once a capture measures it. The human's
hands wire routing and click GUI-only controls; every verification is a
measurement. One-time per project: the print track's input must be the
Master bus (human step, see setup walk-through in
`references/verified-behaviors.md` context). Then iterate:

```
bw.py param 3 0.6            # or lastparam via the user's click
python capture.py --project-dir <proj> --solo <track> --bars 1 --json
```

`capture.py` records the playing groove into a print-track slot, waits for
the WAV in the project's `recordings/` folder, returns hear.py metrics
(f0, harmonic ladder, band shares, level, `--pump` duck/shape,
`--width` per-band side share) as JSON, and
frees the slot — ~7–9 s per iteration when the groove keeps playing between
calls. Launch the scene once at the start (`--scene N` on the first capture);
leave it playing. Done when the measured profile matches the target **on two
consecutive captures** (a reference stem's hear.py output is the natural
target) or the user's ears approve. The repeat is load-bearing: analog-style
patches drift and beat on tens-of-seconds periods, and a single matching
capture can be the drift's lucky phase (measured: identical knobs scored 1.6
then 20.7 against one target). State the target numbers before the first
iteration — a loop without a numeric target is just wiggling knobs.

**Automate the loop with `converge.py`** once the target is a single number
against a single knob: `converge.py --param 3 --metric bands.bass --target 88`
bisects, requires two consecutive in-tolerance captures, and restores the
starting value on any failure. It runs `hear.py` in-process (~6.7 s/iteration
vs ~8.1 s shelling out).

Its **validity gate** is the part that matters: before bisecting it measures
the capture-to-capture noise floor, moves the knob to both extremes, and
refuses to converge if the metric doesn't move by more than that noise —
because a loop tuning a metric the knob does not control will happily report
success. It also prints `WEAK:` when the span is under 4× the noise. Trust a
converged number less than the gate line above it.

**A part that sounds small is often mono, not dull.** `--width` gives the
side share per band against a reference stem's; a dead-centre element reads
~0% where a wide techno hat reads ~25%. Reach for it before EQ when
something "lacks character" — and fix width at the source (pad pan,
`/device/layer/{n}/pan`) rather than with a stereo effect: Chorus+ measured
*zero* movement in the high band while costing top-end level.

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
