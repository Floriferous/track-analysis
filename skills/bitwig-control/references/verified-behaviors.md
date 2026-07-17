# Verified behaviors — the experiment log

Every claim here was tested live (Bitwig 5.3.13, DrivenByMoss 26.6.2, macOS,
2026-07-11). Each entry is observation → implication. Extend this file with the
same discipline: one experiment, one readback, one entry — a claim without a
readback is a guess, not a behavior.

## Verified working

- **Tempo**: `/tempo/raw 130.4` → reads back `130.3999…`. Floats land exactly
  (within float32); no quantization.
- **Track values**: `/track/{n}/volume 0-127` works with dB display feedback
  (`volumeStr`). 64 → −11.8 dB, 100 → −0.2 dB, 101 → +0.1 dB, 102 → +0.3 dB —
  so **128 steps ≈ 0.3 dB granularity near unity, and exact 0.0 dB is
  unreachable**. For finer control raise the DrivenByMoss "Value resolution"
  preference and set `BITWIG_OSC_RESOLUTION` to match. Mute/solo read back.
  Eight sends per track exist (`/track/{n}/send/{1-8}/volume`).
- **Track add**: `/track/add/instrument` and `/track/add/audio` append tracks.
- **Clips**: `insertFile` into an *empty slot* creates the clip and fills it in
  one call — this is the whole flow. The clip takes its **name from the MIDI
  file's track name** (name your pretty_midi instruments). `remove` empties a
  slot. `/scene/{n}/launch` launches a whole row.
- **Device params**: page names, param names, values, and display strings all
  stream. Writes land across the full 0–127 range once the cursor is stable
  (see cursor churn below). Page navigation (`/device/page/{n}/selected`,
  `/device/param/{+,-}`) works.
- **vkb_midi**: notes reach **every record-armed or input-monitoring track**
  simultaneously — it is a broadcast, not a targeted send. Arm exactly one
  track before playing notes.
- **VU as ears**: `/track/{n}/vu`, `/master/vu` stream continuously while the
  listener is up. A note or clip that produces sound shows nonzero VU within
  ~100 ms — the only available "did that make sound?" check. (A silent track
  with a playing clip = instrument missing or routing broken.)
- **Undo/redo**: `/undo`, `/redo` fire (blind — see limits).
- **Adding Bitwig devices end-to-end**: on an *empty instrument track*,
  `/browser/device/after` opens contextually pre-filtered to instruments —
  Drum Machine sat at result 2. `/browser/result/+` steps with reliable
  `isSelected` readback there; `/browser/commit` landed the device (verified:
  `/device/name` = Drum Machine, track renamed). The contextual pre-filter is
  the trick — browsing from a bare track skips the filter-column dance.
- **Samples into audio tracks**: `insertFile` with a `.wav` into an audio
  track's empty slot creates a playing audio clip — verified with a sample-pack
  loop, VU-confirmed sound (track peak 86). No instrument needed. Full sample
  library = fair game for clip-based workflows.
- **Preset browsing end-to-end works, even for plugins**: `/browser/preset` on
  a pinned VST (Diva) listed its indexed presets, the Category filter stepped
  to Bass in one move with live result feedback, `result/+` stepping showed
  reliable `isSelected`, and `commit` loaded the preset — VU-confirmed sound
  after. Plugin *presets* are browsable even though plugin *devices* are not.
- **Device and track removal work**: `/device/remove` (readback: exists 0) and
  `/track/{n}/remove` (bank shifts, explicit track names survive as defaults
  reset). Also live-verified: `/track/{n}/name`, `/scene/{n}/name`.
- **Scene-based arrangement**: filling a track's slot *column* with variations
  and launching rows via `/scene/{n}/launch` gives clean, launch-quantized
  transitions — the previous row's clips stop automatically, both tracks
  switch in sync on the bar. Scenes exist by default (a new project has 8;
  names/colors stream as `/scene/{n}/name` etc.). The same MIDI file can be
  inserted into multiple slots. This is the natural way to sketch an
  arrangement arc (intro → build → drop → fill) from analysis data.

## Verified limits

- **insertFile REPLACES slot content**, and **blank clip names do not mean
  empty slots** (unnamed clips read as ""). `hasContent` is the only truthful
  emptiness check.
- **`clip-create` then `insertFile` is an anti-pattern**: a created clip has
  `hasContent 1` immediately, so the guard (correctly) refuses. `clip-create`
  is only for making an empty clip to record or draw into.
- **Cursor churn**: the cursor device follows GUI selection, so during
  concurrent GUI use `/device/param` writes silently land on whatever the
  human has selected — indistinguishable from failure until read back.
- **Track names are device names**: Bitwig auto-renames tracks after their
  first device ("Inst 1" became "Organ"). Identify tracks by index + type +
  moment-of-reading, never by remembered name.
- **No error replies over OSC**: unknown addresses print a console line in
  Bitwig and are otherwise ignored — but **an out-of-bank index CRASHES the
  extension**: `/track/1/clip/9/launch` against an 8-slot bank killed
  DrivenByMoss with "Index 8 out of bounds for length 8" (dialog offering
  Disable/Restart; the user must click Restart, all OSC dead until then).
  `bw.py` bounds-checks its CLI indices; hand-rolled sends (raw, inline
  scripts) must do their own `1..bank` check.
- **Browser**: no search-by-name and no select-by-index (source-confirmed:
  the module only exposes stepping); result feedback observed stale after
  filter changes; category filters hide container devices (Drum Machine under
  Category=Drums shows only presets). Coarse moves only — except the
  contextual empty-track flow above, which is genuinely usable.
- **Staleness has a mechanism** (source-verified): feedback is change-driven
  with a per-address last-sent cache, so a dropped UDP packet is never
  re-sent and identical-value transitions are suppressed; `/refresh` is a
  parser-level full dump that bypasses the cache. Snapshot reads should ride
  `/refresh` (bw.py does) and re-read after every browser step.
- **Plugins (VST3/CLAP) were not reachable in the OSC browser**: the
  device-insertion view listed only Bitwig natives (no Diva/Serum/Pigments in
  the alphabetical results), no VST/CLAP entry in the Device Type filter, and
  the Location tree is ~100 flat entries deep — blind-stepping it is
  impractical. Unresolved whether a plugins node exists further down. Working
  split: the human adds the plugin; parameter control afterwards is
  device-agnostic (remote-control pages work the same for plugins).
- **Empty containers make no sound**: a freshly added Drum Machine has empty
  pads; loading kits/samples into it is preset-browser or GUI territory.
- **Undo is blind**: history unreadable over OSC, and an OSC tempo change did
  not revert via `/undo`.
- **No position/clip-length feedback**: `/time` writes produce no observable
  readback address; clips expose no length/loop state.

- **Plugin format is readable from the project file**: `strings
  <project>.bwproject` reveals each plugin's identity — CLAP entries show
  `.clap` paths and string IDs (`com.u-he.Diva`) plus `.clap-preset`
  states; VST3s show hex class IDs. The only way to answer "which build is
  this?" without the GUI (OSC feedback carries no format info).
- **Param exposure is a vendor choice, not a format property**: Diva CLAP
  publishes a full model-dependent param set; Serum 2 VST3 publishes zero
  (its params surface only dynamically as GUI-touched, visible to
  `lastparam`). A format swap is worth one test but no guarantee.
- **`lastparam` on a zero-param plugin works** (Serum 2 VST3): reads the
  touched param's name/value, writes land after the prime-with-current
  unlock — but the focus follows EVERY user click (a filter's power button
  stole the focus mid-session and a write toggled it off). `bw.py lastparam
  --expect <name>` guards against writing the wrong control.

## Incidents (the evidence behind SKILL.md's rules)

- Real project clips were overwritten because empty clip *names* were read as
  empty *slots* → the hasContent guard and the sandbox rule.
- A track volume was changed without recording its original value; restoring
  it meant guessing → snapshot before mutating.
- A run of param writes silently landed on the wrong device while the user
  clicked around the GUI → the cockpit rule, pinning, and readback-verified
  writes.

## Source-verified, awaiting live confirmation

Read in the DrivenByMoss 26.6.2 implementation (see osc-protocol.md for the
full surface), not yet exercised against a live project:

- `/scene/add` (empty scene) and `/scene/create` (captures playing clips)
- `/track/{n}/remove`, `/duplicate`, `/name`, `/color`; `/track/add/effect`
- `/device/lastparam/value` (writes the GUI-focused parameter),
  `/device/remove`, `/duplicate`, `/bypass`; layer/drumpad subtrees; `/eq` tree
- `/project/save`, `/project/engine`, project-level remote controls
- `/time {beats}` playhead writes — feedback is strings only
  (`/time/str`, `/beat/str`); numeric position is never echoed
- Markers are launch-only (`/marker/{n}/launch`) — no create over OSC
- `/action/{1-20}` fires Bitwig actions pre-bound in DrivenByMoss settings
- Floats truncate to int in most handlers (`toInteger`) — `0.5` becomes `0`
- `/vkb_midi` notes are remapped through the current scale (out-of-scale
  notes silently dropped) and a fixed-accent setting can override velocities

## Untested

Banks beyond 8 (`/track/bank/+`), value resolutions above 128,
`/browser/preset` commit flow end-to-end, automation writing
(`/autowrite`, `/automationWriteMode`).
