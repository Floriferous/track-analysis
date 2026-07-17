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

## Writing files (the untested frontier)

Everything needed is known: encode CBOR → zstd-compress → fill in
uncompressed size + md5 → assemble. Not yet attempted; when first tried,
verify by loading in Serum (Load MIDI Map for maps; preset browser for
presets) and measuring, before trusting the encoder. Obvious applications:
extending the CC roster without MIDI-Learn clicking (needs the paramID from
the scheme + one measured confirmation), and eventually authoring patches
directly (`kParam*` values are plain floats).
