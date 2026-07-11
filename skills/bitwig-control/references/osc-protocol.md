# DrivenByMoss OSC — implementation-verified reference

Verified against the DrivenByMoss 26.6.2 source. **Ground truth is the
implementation**: `opensrc/DrivenByMoss/src/main/java/de/mossgrabers/controller/osc/`
— `protocol/OSCParser.java`+`OSCWriter.java` for wire mechanics, one
`module/*Module.java` per address family. Read the module before concluding an
address doesn't exist. If the `opensrc/` symlink is missing:
`npx opensrc fetch git-moss/DrivenByMoss`, symlink the printed path to
`opensrc/DrivenByMoss`.

## Wire mechanics (why the link behaves as it does)

- **Feedback is change-driven and cache-deduplicated.** Bitwig's flush tick
  batches only values that differ from a per-address last-sent cache, framed
  by `/update 1` … `/update 0`, in bundles of ≤100 messages ~10 ms apart. A
  dropped UDP packet is never re-sent (the cache thinks it went out), so a
  client's view can silently drift.
- **`/refresh` is the recovery**: handled in the parser itself, it forces a
  full cache-bypassing dump of everything. Send it on connect and whenever
  state looks stale.
- **No idle heartbeat.** `/time/str` and `/beat/str` stream while the
  transport moves; when idle and unchanged, silence is normal. Liveness check
  = `/refresh` and expect a dump.
- **Numeric args are truncated to int** by most handlers (`toInteger`):
  sending `0.5` to a volume yields `0`. Scale to the configured resolution
  (default 0–127) and send integers. True-float exceptions: `/tempo/raw`,
  `/tempo/+ -`, `/time`, `/launcher/postRecordingTimeOffset`.
- **Triggers**: no argument at all, or any number > 0, fires; `0` is
  false/release. Toggle commands (`mute`, `click`, `repeat`…) toggle when the
  argument is *absent* and set when it's `0`/`1`.
- **Booleans** arrive as `0`/`1`; **colors** are strings `rgb(r,g,b)` (0–255)
  both ways; strings are ASCII-sanitized.
- **Bad commands are visible to the user**: unknown addresses and illegal
  parameters print `Unknown OSC command:` / `Illegal parameter:` lines in
  Bitwig's controller console. **Out-of-bank indices are worse than bad**:
  an uncaught `ArrayIndexOutOfBoundsException` crashes the whole extension
  (observed with clip index 9 on an 8-slot bank) — keep every `{1-N}` within
  the bank page size.
- Receive port (default 8000) and send port (9000) must differ; send host/port
  changes need a Bitwig restart. "Bank page size" (default 8) bounds every
  `{1-N}` index below; "Value resolution" (128/1024/16384) sets value ranges.

## Transport (`TransportModule`)

| Address | Args | Notes |
|---|---|---|
| `/play`, `/stop`, `/record`, `/restart`, `/playbutton` | trigger | stop twice = stop-and-rewind |
| `/tempo/raw` | float BPM | also `/tempo/tap`, `/tempo/+ [step]`, `/tempo/- [step]` |
| `/time` | float beats | absolute playhead position; feedback is strings only: `/time/str`, `/beat/str` |
| `/position/{+,-,++,--,start}` | | jog fine/coarse/home |
| `/click` | toggle/bool | `/click/volume {int}`, `/click/ticks`, `/click/preroll`, `/preroll {bars}` |
| `/overdub[/launcher]`, `/repeat`, `/punchIn`, `/punchOut` | toggle/bool | |
| `/autowrite[/launcher]` | trigger | `/automationWriteMode {LATCH\|TOUCH\|WRITE}` |
| `/quantize` | trigger | quantizes the cursor note clip, amount 1.0 |
| `/crossfade` | int | + `/crossfade/reset` |
| `/launcher/defaultQuantization` | string | e.g. `1/4`; also `postRecordingAction`, `postRecordingTimeOffset` |

## Tracks (`TrackModule`) — also `/master/...` and `/track/selected/...`

Per track `/track/{1-N}/`: `volume`, `pan` (int; each with `/indicate`,
`/reset`, `/touched`), `mute`, `solo`, `recarm`, `monitor`, `autoMonitor`
(toggle/bool), `select`, `duplicate`, `remove`, `activated`, `name {str}`,
`color {rgb()}`, `crossfadeMode/{A,B,AB}`, `recordQuantization {str}`,
`enter` (descend into group), `send/{1-N}/volume` (+variants),
`clip/...` (below), `clip/stop`, `clip/returntoarrangement`.

Bank level: `/track/add/{instrument,audio,effect}`, `/track/{+,-}` (move
selection), `/track/bank/{+,-}` (scroll window), `/track/bank/page/{+,-}`,
`/track/parent` (up out of group), `/track/stop[Alt]`, `/track/toggleBank`
(main↔effect banks), `/track/vu {bool}` (enable VU feedback!),
`/track/param/{1-N}/value` (the **cursor track's remote controls**) +
`/track/page/{n}` page selection.

Feedback per track: `exists`, `type`, `name`, `volume(+Str)`, `pan(+Str)`,
`mute`, `solo`, `recarm`, `monitor`, `isGroup`, `canHoldNotes`, `position`,
`vu` (when enabled), `color`, full `clip/{n}/` blocks
(`hasContent`, `isPlaying`, `isPlayingQueued`, `isRecording`, `name`, `color`…).

## Clips — two surfaces

**Explicit slot** `/track/{t}/clip/{c}/`: `launch {>0 press, ≤0 release}`,
`launchAlt`, `create {beats}`, `insertFile {abs path}` (replaces slot content;
audio or MIDI), `record`, `duplicate`, `remove`, `select`, `color`.

**Cursor clip** `/clip/` (selected slot of cursor track): `launch`,
`launchAlt`, `create`, `insertFile`, `record`, `name {str}`, `color`,
`quantize`, `pinned`, `{+,-}` (move slot selection), `stop[Alt]` (cursor
track), `stopall[Alt]` (everything). No remove/duplicate here — those are
explicit-slot only. No note-level editing anywhere in the OSC surface.

## Scenes (`SceneModule`)

`/scene/add` (new empty scene), `/scene/create` (new scene **from currently
playing clips** — capture!), `/scene/{n}/launch`, `/scene/{n}/{select,
duplicate,remove}`, `/scene/{n}/name {str}`, `/scene/{n}/color {rgb()}`,
`/scene/{+,-}` scroll, `/scene/bank/{+,-}`. Quirk: `/scene/{n}/launchAlt` is
identical to `launch` in 26.6.2 (alt flag hard-coded false).

## Device (`DeviceModule`) — also `/primary/` (first instrument) and `/eq/`

| Address | Args | Notes |
|---|---|---|
| `/device/param/{1-N}/value` | int | + `/indicate`, `/reset`, `/touched {bool}` (explicit touch protocol — value writes alone don't touch) |
| `/device/page/{n}` or `/page/select {n}` | | direct page jump; `/device/param/{+,-}` scroll pages |
| `/device/{+,-}` | trigger | walk device chain; `/device/sibling/{n}/select`, `/device/bank/page/{+,-}` |
| `/device/pinned` | toggle/bool | hold cursor against GUI selection |
| `/device/bypass` | trigger | toggle enabled |
| `/device/expand`, `/device/window`, `/device/parameters` | trigger | UI toggles |
| `/device/duplicate`, `/device/remove` | trigger | |
| `/device/lastparam/{value,indicate,reset,touched}` | | **writes the GUI-focused parameter, bypassing pages** — "click the knob, I'll turn it" |
| `/device/layer/{n\|selected\|+,-}/...` | | volume/pan/mute/solo/sends/name/enter per layer; same tree at `/device/drumpad/{n}/` when the device has pads |
| `/eq/add` | trigger | add an EQ to cursor track; `/eq/{type,gain,freq,q}/{band}` edit bands |

Feedback: `/device/{exists,name,bypass,expand,window,pinned}`, full param
blocks with `valueStr`, page names + `/device/page/selected/name`, sibling
names, layer/drumpad blocks.

## Project & application

`/project/{+,-}` switch projects, `/project/engine {toggle/bool}`,
**`/project/save`**, `/project/param/{1-N}/value` (project-level remote
controls) + page nav. `/undo`, `/redo` (GlobalModule — blind, no history
feedback). `/action/{1-20}`: fires Bitwig actions **pre-bound in the
DrivenByMoss settings GUI** (any Bitwig action ID can be bound to a slot —
a configurable escape hatch, but not arbitrary IDs over the wire).

## Browser (`BrowserModule`)

`/browser/preset` (browse presets of cursor device), `/browser/device
[after|before]` (insert relative to cursor device), `/browser/tab/{+,-}`,
`/browser/filter/{1-6}/{+,-,reset}`, `/browser/result/{+,-}`,
`/browser/commit`, `/browser/cancel`. **No select-by-index and no
search-by-name** — stepping only; feedback for filter/result windows rides
the same flush diffing, so re-read after every step and `/refresh` when in
doubt.

## Notes & MIDI (`MidiModule`)

`/vkb_midi/{ch 1-16}/note/{0-127} {vel}` (0 = off) — sent into the surface's
note input, i.e. whatever track(s) are armed/monitoring; remapped through the
current scale (out-of-scale notes are *dropped* — octave shifts via
`/note/{+,-}`). `/drum/{note}` uses the drum matrix instead. `/cc/{n}`,
`/pitchbend` (64 = center), `/aftertouch[/{note}]`. `/vkb_midi/velocity {int}`
sets a fixed accent that **overrides all incoming velocities** (0 disables).
Note repeat: `/vkb_midi/noterepeat/{isActive,period,length}` (`1/4`…`1/32t`).

## Markers, layout, panels

`/marker/{n}/launch` and `/marker/bank/{+,-}` — markers can be jumped to but
**not created** over OSC. Feedback: `/marker/{n}/{exists,name,color}`.
`/layout {ARRANGE|MIX|EDIT}`, `/panel/{noteEditor,automationEditor,devices,
mixer,fullscreen}`, `/arranger/*` and `/mixer/*` visibility toggles.
