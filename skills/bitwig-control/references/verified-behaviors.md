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

## Verified limits

- **insertFile REPLACES slot content**, and **blank clip names do not mean
  empty slots** (unnamed clips read as ""). `hasContent` is the only truthful
  check. Learned by overwriting real project clips.
- **`clip-create` then `insertFile` is an anti-pattern**: a created clip has
  `hasContent 1` immediately, so the guard (correctly) refuses. `clip-create`
  is only for making an empty clip to record or draw into.
- **Cursor churn**: the cursor device follows GUI selection. While the user
  clicks around Bitwig, `/device/param` writes silently land on whatever *they*
  selected — observed as a run of ignored/misdirected writes during concurrent
  GUI use, indistinguishable from failure until read back. Protocol: announce
  device edits, `raw /device/pinned 1` to hold the cursor, and treat the
  readback (bw.py `param` does it automatically) as the write.
- **Track names are device names**: Bitwig auto-renames tracks after their
  first device ("Inst 1" became "Organ"). Identify tracks by index + type +
  moment-of-reading, never by remembered name.
- **No error replies ever**: wrong addresses and out-of-window indices vanish
  silently. Feedback delta is the only success signal.
- **Browser**: no search-by-name; result feedback can stay stale after filter
  changes (survives `/refresh`); category filters hide container devices (Drum
  Machine under Category=Drums shows only presets). Coarse moves only.
- **Undo is blind**: history unreadable, and an OSC tempo change did not revert
  via `/undo`. After a mistake in a real project, narrate exactly what changed
  and let the user drive Cmd+Z.
- **No position/clip-length feedback**: `/time` writes produce no observable
  readback address; clips expose no length/loop state.

## Field rules (from incidents)

1. **Snapshot before mutating.** Record the readback value of anything you're
   about to change (a volume was changed here without noting the original —
   restoring it meant guessing).
2. **Sandbox first.** New experiments run in a scratch project; the user's real
   project is not a lab.
3. **A write isn't done until read back.** UDP + no error replies means
   fire-and-forget is fire-and-hope.

## Untested

Track remove/reorder, banks beyond 8 (`/track/bank/+`), markers, `insertFile`
with audio files, `/time` write effect (unverifiable without position
feedback), value resolutions above 128, `/browser/preset` commit flow
end-to-end, automation writing, cue markers, project save.
