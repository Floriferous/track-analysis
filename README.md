# track-analysis

Analyze electronic music tracks (WAV/MP3/AIFF/FLAC) into discussable, timestamped artifacts — beat/bar grids, drum-pattern grids, spectrograms, arrangement maps, loudness, stems, kick anatomy, sidechain pump, and bass-note placement — plus DAW-ready MIDI export and a reference-comparison tool.

Built as [Claude Code skills](https://code.claude.com/docs): copy the folders under `skills/` into your project's `.claude/skills/` and Claude will self-trigger. The scripts also work standalone.

Four skills that pair:

- **[`track-analysis`](skills/track-analysis/SKILL.md)** — audio in, understanding out: dossiers, grids, spectrograms, deep stem analysis, MIDI export. See [`dossier-format.md`](skills/track-analysis/references/dossier-format.md) (schemas, grid notation, failure modes) and [`sources.md`](skills/track-analysis/references/sources.md) (research and upgrade paths).
- **[`bitwig-control`](skills/bitwig-control/SKILL.md)** — understanding in, DAW out: drives Bitwig Studio over OSC (via [DrivenByMoss](https://www.mossgrabers.de/Software/Bitwig/Bitwig.html)) — tempo/transport, injecting exported grooves into clip slots, launching clips, synth parameter editing, preset browsing, and a measured capture-and-tune loop. See [`osc-protocol.md`](skills/bitwig-control/references/osc-protocol.md).
- **[`bitwig-devices`](skills/bitwig-devices/SKILL.md)** — the recipe library: per-device setup subdocuments (parameter maps, raw↔display anchors, GUI-only boundaries, verified presets), grown one device per session.
- **[`diva`](skills/diva/SKILL.md)** — the first dedicated synth skill (complex synths get their own): u-he Diva's model-dependent controllable surface, manual-backed architecture map, measured patch recipes. (Serum 2 planned next.)

Together they close the loop: analyze a reference → export its groove → recreate it in Bitwig → bounce and re-analyze to compare.

Scope: steady-tempo 4/4 electronic music (techno, house, psy, and neighbors).
