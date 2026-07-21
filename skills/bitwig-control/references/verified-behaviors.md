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
- **Page addressing is window-relative and silently sticky at the ends**
  (live, Diva 18-page walk): `/device/page/{n}/selected` selects slot *n* of
  the current 8-wide window — not page *n* of the device — and
  `/device/param/{+,-}` steps the selected page by one, as a **silent no-op
  past either end** of the page list. A page index from an enumeration is
  therefore meaningless as a jump target (incident: "page 12" of a 13-page
  walk selected the *reverb* and two writes landed on its Wet). `bw.py page
  <name>` is the safe form: it rewinds, steps, and verifies
  `/device/page/selected/name` before returning.

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

- **vkb_midi CC injection can die while notes keep working** (2026-07-20):
  `/vkb_midi/1/cc/*` stopped reaching a record-armed track's plugin
  (proven by the receiver's own MIDI-Learn hearing nothing) while
  `/vkb_midi/1/note/*` still sounded (VU 58) — and it survived a
  controller power-cycle, a fresh plugin instance, and a full Bitwig
  restart. Root cause unfound. Workaround, now the standing CC transport:
  a second IAC bus ("claude-cc") into a Generic MIDI Keyboard controller —
  CCs verified arriving. Note the OSC controller *requires* a MIDI-in port
  assignment to stay enabled (it holds IAC Bus 1); never reassign its port.

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

- **A COLD continuous write is silently swallowed — prime it** (diagnosed
  2026-07-21; supersedes three separate "this address is broken" reports
  for `/track/{n}/volume`, `/eq/freq/{band}`, and `/device/layer/{n}/pan`,
  which were all this one behaviour).

  A numeric write to a continuous parameter lands only if that address has
  been written recently. **Prime it: send the current value, wait ~0.25 s,
  then send the target — from one process.** Once warm, lone writes land
  reliably (5/5 sweep on a warmed track volume). The prime value need not
  match the current one (40→40 worked as well as 64→40), so this is not
  takeover. A GUI touch warms an address too — which is why "nudge the
  fader once" looked like the unlock; that's one way to prime, not the
  mechanism.

  `bw.py`'s `cmd_param` has always primed ("some states reject a cold
  absolute write"), which is exactly why `param` never showed the bug and
  `raw` did. Root cause is not identified in the source — `TrackModule` →
  `ChannelImpl.setVolume` → `RangedValueImpl.setValue` →
  `rangedValue.set(value, upperBound)` all read correctly.

  **Now automated** (2026-07-21): `bw.py` has a single `send()` write path
  with an anchored regex allowlist `is_continuous()` of every address that
  ends in a value write, derived by reading the OSC modules. It is anchored
  (`$`) because the `/indicate`, `/reset` and `/touched` children of those
  same parents are triggers — `/track/1/volume` primes, `/track/1/volume/reset`
  must not. Classification is unit-tested (29 cases). The denylist that must
  NEVER be primed, by failure mode: fire-twice (`clip/launch`, `scene/launch`,
  `create`, `record`, `duplicate`, `remove`, `add`, `undo`), relative steppers
  (`/device/{+,-}`, every `bank/page/{+,-}`, `/browser/*/{+,-}`), argument-
  ignoring toggles (`/device/bypass`, `/overdub`, `/panel/*`), asymmetric
  transport (`/stop` rewinds on the second send), and MIDI events
  (`/vkb_midi/*` — a primed note-on is two notes).

  Related, from the same source read: **DrivenByMoss accepts exactly ONE
  argument per message.** `OSCParser` passes a multi-arg `Object[]` straight
  into `toInteger`, which throws — so multi-arg sends fail silently
  everywhere except `/vkb_midi/{ch}/note`. `bw.py raw` now refuses them.

  Discrete writes (`mute`, `solo`, `launch`, `name`, `/eq/type`,
  `volume/reset`) are never affected — they land cold, every time.

  **Read the value back after every continuous write.** A dropped write is
  silent and indistinguishable from success; this is the readback rule with
  teeth.

  Raw scales worth not re-deriving: track volume raw 69 = −10.0 dB, ~0.38
  dB/step · Compressor+ Make-up (a fine substitute fader, post-compression
  so it won't disturb a calibrated duck) raw 64 = 0.0 dB, 39 = −9.3,
  ~0.36 dB/step · EQ+ freq is log, raw 25 = 80 Hz and +13 raw = one octave
  (raw ≈ 25 + 13·log2(f/80)), gain raw 64 = 0.0 dB / 80 = +7.8, Q raw 64 =
  1.00 / 100 = 8.33.

  For EQ+ specifically, prefer the **param path** over the `/eq` tree
  anyway: `/eq/add` leaves EQ+ as the cursor device, so pin it and use
  pages **Gains / Freqs / Qs**, one band per index — you get `[OK]` plus a
  display-value readback for free.
- **`page <Name>` can fail silently — always verify the page landed**
  (2026-07-21): `bw.py page Qs` on EQ+ printed `page: Freqs` and left the
  cursor on Freqs; the next `param 3` write then hit *3 Freq*, sending a
  102 Hz bell band to 2.67 kHz. `page Gains` and `page Freqs` on the same
  device worked. Cause not established (last-page? two-char name?), but the
  workaround is solid: **`/device/page/{n}` by index landed on Qs first
  try**, and `/device/page/selected/name` reads back the current page for
  confirmation. Rule: after any `page`, read `params` (or
  `page/selected/name`) and check the page header matches *before* writing —
  a page switch also needs ~1.5-2 s to settle, and a write issued into that
  window lands on the old page.
- **Browser Device Type filter does not reach the result list** (2026-07-21,
  concrete repro for the "hand deep filter navigation to the user" rule):
  `/browser/device after`, then two `/browser/filter/6/+` — the filter reads
  back `item/3/isSelected 1 = Instrument`, but `/browser/result/*` still
  lists Audio FX (Amp, Blur, Chorus…) unchanged. Survived a 2.5 s settle, a
  `/refresh` (every `bw.py state` sends one), and a `/browser/result/+`
  nudge. The *preset* browser's Category filter (`filter/3`) DOES drive its
  results — that flow worked twice this session (Bass, Pad) — so the defect
  is specific to the device browser's Device Type column. Don't try to
  enumerate installed instruments over OSC; ask the user to read the list.
  Note the preset-browser filter list is a **scrolling window**: after
  stepping, item indices shift (11 `+` steps from "Any Category" landed on
  Vocal with "Pad" now at item 1), so re-read the list and step back rather
  than counting from the original indices.

### Drum Machine (all 2026-07-21)

- **Reaching the container is free; reaching a specific pad needs a click.**
  With the cursor on a track-level device, `device -` walks *back onto the
  Drum Machine* — that is the way out of the nested-pad trap, no GUI
  needed. What still needs the user is descending into one **particular
  pad's** device, and they must click the **device box, not the pad**
  (clicking a pad only changes which chain is displayed). Once inside a
  pad, `/device/{+,-}` walks that pad's siblings only and re-selecting the
  track will not reset the depth — a stale pad cursor survives track
  selects and browser sessions, so **read `/device/name` back after every
  requested click, then pin.**
- **`/device/layer/{n}/{exists,name,pan}` enumerates the kit** from the
  container — pad names without a single GUI question.
- **Pad pan is the hat-width lever.** Measured high-band side share on two
  v9 hat pads: centred **7.7%** → 48/80 **11.8%** → 34/96 **20.9%** →
  26/104 **27.3%** → **30/100 = 23.3%** against a 24.2% reference.
  **Chorus+ is not a substitute** — at Bal/Width 100%, Tone 85%, Depth
  25-65%, Mix 25-70% it never moved high-band side share off 7.7% while
  costing real top end (mix high 1.0% → 0.3% at 70% wet). It widens
  low-mid/mid only.
- **Probe the note map — never assume GM.** This kit had **only pads 37 and
  42 loaded, and 42 was the OPEN hat**. A GM-shaped clip (42 closed, 46
  open) therefore put the open hat quietly on the beats and left **every
  offbeat silent**, which reads as "thin, needs +6 dB" rather than
  "broken". Method: one clip per candidate note, insert, **relaunch the
  scene** (`clip-insert-file` leaves the slot stopped — an un-relaunched
  probe fakes a negative on every note), capture 1 bar, compare rms. Silent
  reads exactly **−240 dBFS**, so the signal is unambiguous; ~10 captures
  covers 36-47.
- **Clearing solo does not reliably clear the mutes it implied** (2026-07-21).
  After soloed captures, two unrelated tracks were left `mute 1`; the next
  full-mix measurement then read mid 0.3 % / high 0.0 % — the parts simply
  weren't there, with no error anywhere. In an unattended loop this poisons
  every subsequent number. `capture.py` now snapshots mutes before a soloed
  capture and restores any that changed; if you solo by hand, check
  `/track/{n}/mute` afterwards.
- **A pump measurement is only valid if the sidechain is the ONLY thing
  modulating that band** (2026-07-21). Measuring duck on a chord bus whose
  patch has `Sustain 0` and re-articulates once per bar read **93 %** — the
  patch's own decay envelope, folded onto the beat, is indistinguishable
  from a duck. Narrowing the band did not help (same 93 % at 350-2000 as at
  300-6000) because the confound is the source, not the neighbours. Before
  trusting a duck figure, confirm the ducked element is *sustained* across
  the beat; otherwise calibrate the compressor against the threshold→depth
  table (bitwig-devices/compressor-plus.md) and judge by ear. An earlier
  68-71 % reading on the same bus carried the same inflation, so a
  "corrected" target derived from it was withdrawn.
- **Isolate one variable per probe, or you will misread the result.** Twice
  in one session: an **Output A/B identifies the device, not the note** —
  zeroing `v9 Hat Open`'s Output under a 42/46/37 clip gave a clean 7.7 dB
  rms drop that read as "note 46 works", when the drop came from note *42*;
  only a single-note clip isolates a mapping. And **a solo capture compared
  against a reference *stem*** (hats alone vs a drums stem carrying a mono
  kick) made Chorus+ look like it was widening the mix. Pick a band the
  isolated source actually owns — the kick measures 0.0% above 2 kHz, so
  only the high band was a fair test. Throughout, **compare rms, not
  peak**: peak moved 0.1 dB where rms moved 7.7, because other elements'
  transients dominate peak.
- **Scene launches stop the print-track recording — even via EMPTY slots**
  (2026-07-20, two dead bounces): a scene fires every track's slot button in
  its row, and an empty slot button is a *stop* button, so any
  `/scene/{n}/launch` during a long capture kills the recording clip on the
  print track. For arrangement-length bounces, drive sections with
  **per-track clip launches + `/track/{n}/stop`** and never touch the print
  track's rows (verified working: 76-bar bounce). Also: launcher→arranger
  recording did not happen via `/record` + `/play` + scene launches (three
  variants, arranger stayed empty; per-track arm on/off made no difference)
  — the correct Bitwig gesture over OSC is unresolved; audio bounce via the
  print track is the proven way to render a performance.
