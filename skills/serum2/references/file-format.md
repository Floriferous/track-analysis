# Xfer's file container (XferJson): .SerumMIDIMap and .SerumPreset

Reverse-engineered and verified 2026-07-17 against three files (the factory
macros map, our saved 22-binding map, factory preset "PN - Piano Dance",
user preset "psy-bass"). Decoder: `scripts/serumfile.py` (info / map / dump).

## Container layout

| bytes | content |
|---|---|
| 9 | magic `"XferJson\x00"` |
| 4 | u32le manifest length |
| 4 | u32le 0 |
| n | JSON manifest |
| 4 | u32le uncompressed payload size |
| 4 | u32le 2 (payload format version) |
| … | one zstd frame, compressing a CBOR document |

`manifest["hash"] = md5(zstd frame bytes)` — verified on all three files.
Integrity only, not authentication: hand-written files just need a matching
hash. Manifest carries `fileType` ("SerumMIDIMap" / "SerumPreset"),
`product` "Serum2", vendor/url/version, and for presets the
author/name/description/tags shown in Serum's browser.

## SerumMIDIMap payload

```json
{"fileType": "SerumMIDIMap", "product": "2", "version": …,
 "midiMap": [ {"ccNum": 22, "paramIDs": [2000003]}, … ]}
```

One entry per CC; `paramIDs` is a list (one CC can drive several params —
the factory macros map uses one each). paramID semantics: see the scheme in
`control-surface.md`.

## SerumPreset payload

A module tree keyed by module name — observed top-level keys include
`Oscillator0..4`, `WTOsc`, `SpectralOsc`, `GranularOsc`, `MultiSampleOsc`,
`Filter`, `VoiceFilter0/1`, `Env0..3`, `LFO0..9`, `Macro0..7`,
`ModSlot0..63`, `FXRack0..2`, `Arp0`/`ArpClip*`, `MidiClip*`, `Global0`,
`SerumGUI`, plus scalar metadata (presetName, mpe*, version…).

Each module holds `plainParams`: **sparse, name-keyed** — only
values changed from default are stored, by internal name, e.g.

```json
"Global0": {"plainParams": {"kParamMasterVolume": 0.3005, "kParamPolyCount": 32.0}},
"Env0":    {"plainParams": {"kParamSustain": 0.8947, "kParamRelease": 0.5198}}
```

The string `"default"` stands in for an untouched module. Note the two
naming systems: presets use `kParam*` *names*, MIDI maps use numeric
*paramIDs*; no file observed so far carries the name↔ID table.

## Writing files — PROVEN (2026-07-20)

`serumfile.py addcc` / `setparam` (plus `write_container()` for anything
else) encode CBOR → zstd → sizes + md5. Every write self-checks by decoding
itself. Live-verified both ways:

- **MIDI map**: a 23-binding map written by the encoder was loaded by Serum
  (menu → Load MIDI Map, no error) and Serum's own *Save MIDI Map* dump of
  the result was **payload-identical key-for-key** to the written file —
  the strongest possible readback.
- **Preset**: two copies of a user preset with `Global0.kParamMasterVolume`
  set to 0.38 / 0.90 (original 0.19) were indexed by Serum's browser,
  loaded errorlessly, and measured monotonically louder (RMS −21.6 →
  −20.6 → −17.6; the value→dB curve is Serum's own taper, not linear).

Byte-fidelity notes (from diffing against Serum-written files): the JSON
manifest must be compact (`","`/`":"` separators — byte-identical then);
Serum writes CBOR map keys in plain alphabetical order (round-tripping
preserves it; RFC-canonical sorting does NOT match) and uses
smallest-width floats where cbor2 emits float64 — Serum's parser accepts
both widths (its own factory files mix them).

**The save-back readback**: Serum has no live binding query, but *Save MIDI
Map* → decode is a full readback of its current CC state. Use it whenever
"is the map actually loaded?" matters — GUI right-click menus show per-knob
CC badges too, but the file is measurable.
