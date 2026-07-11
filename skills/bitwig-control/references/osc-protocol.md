# DrivenByMoss OSC — the addresses that matter

Curated from the official protocol doc and manual (DrivenByMoss 26.6.2). Full
reference: <https://github.com/git-moss/DrivenByMoss-Documentation/blob/master/Generic-Tools-Protocols/Open-Sound-Control-(OSC).md>
and the manual PDF bundled in the download.

**Ground truth is the implementation**: `opensrc/DrivenByMoss/src/main/java/
de/mossgrabers/controller/osc/module/` — one module class per address family
(Transport, Track, Clip, Scene, Device, Browser, Midi, Marker, Project,
Global). Read the module before concluding an address doesn't exist; the docs
lag the code (e.g. `/scene/add` exists in SceneModule but not in this table).
If the `opensrc/` symlink is missing: `npx opensrc fetch git-moss/DrivenByMoss`
then symlink the printed path to `opensrc/DrivenByMoss`.

All indices are **bank-relative 1..8** (a window onto the project, not absolute
positions). `/track/bank/{+,-}` and `/device/bank/page/{+,-}` slide the window.
Bank size is a DrivenByMoss preference (default 8).

## Transport

| Address | Args | Notes |
|---|---|---|
| `/play`, `/stop`, `/record` | none or `{0,1}` | |
| `/tempo/raw` | `{0-666}` | BPM, float OK |
| `/time` | position | playback position |
| `/click` | `{0,1}` | metronome |

## Clips (the groove-injection path)

| Address | Args | Notes |
|---|---|---|
| `/track/{1-8}/clip/{1-8}/create` | `{beats}` | new empty clip of that length |
| `/track/{1-8}/clip/{1-8}/insertFile` | `{path}` | loads a MIDI or audio file into the slot — absolute path; replaces existing slot content |
| `/track/{1-8}/clip/{1-8}/launch` | launch=1, release=0 | |
| `/track/{1-8}/clip/{1-8}/select` | | |
| `/clip/create` | `{beats}` | on the cursor track |
| `/clip/stopall` | | stop all clips |
| `/scene/{1-8}/launch` | | launch a whole scene row (verified) |

## Tracks

`/track/{1-8}/volume {0-RES}`, `/pan`, `/mute {0,1}`, `/solo`, `/recarm`,
`/select`, `/track/bank/{+,-}`. Feedback includes `/track/{n}/name` etc.

`/track/add/instrument` and `/track/add/audio` — append a new track (verified
working; the new track lands at the end of the bank).

Feedback extras: `/track/{n}/vu` (live level meter — the "hearing" proxy),
`/track/{n}/send/{1-8}/volume(+Str)`, `/master/vu`, `/track/selected/*`.

## Device / synth editing (cursor device)

| Address | Args | Notes |
|---|---|---|
| `/device/param/{1-8}/value` | `{0-RES}` | RES = "Value resolution" preference, default 128 → 0-127 |
| `/device/page/{1-8}/selected` | | jump to a remote-controls page |
| `/device/param/{+,-}` | | next/previous page |
| `/device/{+,-}` | | walk the device chain |
| `/device/sibling/{1-8}/selected` | | |
| `/device/expand`, `/device/window` | `{0,1}` | open plugin UI |
| `/device/pinned` | `{0,1}` | stop cursor following selection |

Feedback: `/device/name`, `/device/page/selected/name`, `/device/param/{n}/name`,
`/device/param/{n}/value` (+ display string). Listen before you tweak.

## Browser (load devices & presets)

Flow: open → filter → step results → commit.

| Address | Notes |
|---|---|
| `/browser/device/after` (or `/before`) | insert a device relative to cursor device |
| `/browser/preset` | swap preset of cursor device |
| `/browser/tab/{+,-}` | Devices / Presets / Multisamples ... |
| `/browser/filter/{1-6}/{+,-}` and `/reset` | columns: Favorites, Location, Type, Category, Tags, Creator |
| `/browser/result/{+,-}` | step result list |
| `/browser/commit` / `/browser/cancel` | |

Feedback streams the visible filter/result names — step, read, step.

## Real-time notes (virtual keyboard)

| Address | Args |
|---|---|
| `/vkb_midi/{ch 1-16}/note/{0-127}` | `{velocity 0-127}`, 0 = note off |
| `/vkb_midi/{ch}/drum/{0-127}` | same, drum-pad variant |
| `/vkb_midi/{ch}/cc/{0-127}` | `{0-127}` |
| `/vkb_midi/{ch}/pitchbend` | `{0-127}`, 64 = center |
| `/vkb_midi/{ch}/aftertouch[/{note}]` | `{0-127}` |

Notes go to whatever track is record-armed/monitoring. Timing rides on UDP —
fine for auditioning, do not use for precision groove recording (insertFile
preserves file timing exactly; vkb_midi does not).

## Global

`/refresh` — resend all state (how `bw.py` snapshots). DrivenByMoss also emits
heartbeat pings; any feedback at all proves the link works.

`/undo`, `/redo` — fire Bitwig's undo/redo; history is not exposed over OSC.
