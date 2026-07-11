# track-analysis

Analyze electronic music tracks (WAV/MP3) into discussable, timestamped artifacts — beat/bar grids, drum-pattern grids, spectrograms, arrangement maps, loudness, stems, kick anatomy, sidechain pump, and bass-note placement — plus DAW-ready MIDI export and a reference-comparison tool.

Built as a [Claude Code skill](https://code.claude.com/docs): drop this repo (or a copy of it) into `.claude/skills/track-analysis/` and Claude will self-trigger on audio-analysis questions. The scripts also work standalone.

- **Start here:** [`SKILL.md`](SKILL.md) — what runs when, setup, trust boundaries.
- [`references/dossier-format.md`](references/dossier-format.md) — output schemas, grid notation, how to read each artifact, known failure modes.
- [`references/sources.md`](references/sources.md) — the research and tools behind the design, and upgrade paths.

Scope: steady-tempo 4/4 electronic music (techno, house, psy, and neighbors).
