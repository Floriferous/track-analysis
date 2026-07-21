# track-analysis

Analyze electronic music tracks (WAV/MP3/AIFF/FLAC) into discussable, timestamped artifacts — beat/bar grids, drum-pattern grids, spectrograms, arrangement maps, loudness, stems, kick anatomy, sidechain pump, and bass-note placement — plus DAW-ready MIDI export and a reference-comparison tool.

Built as [Claude Code skills](https://code.claude.com/docs): copy the folders under `skills/` into your project's `.claude/skills/` and Claude will self-trigger. The scripts also work standalone.

Six skills that pair:

- **[`track-analysis`](skills/track-analysis/SKILL.md)** — audio in, understanding out: dossiers, grids, spectrograms, deep stem analysis, MIDI export. `targets.py` emits the per-element numeric target sheet a recreation is converged onto; `midi.py --check` refuses to write musically-nonsense exports. See [`dossier-format.md`](skills/track-analysis/references/dossier-format.md) (schemas, grid notation, failure modes) and [`sources.md`](skills/track-analysis/references/sources.md) (research and upgrade paths).
- **[`bitwig-control`](skills/bitwig-control/SKILL.md)** — understanding in, DAW out: drives Bitwig Studio over OSC (via [DrivenByMoss](https://www.mossgrabers.de/Software/Bitwig/Bitwig.html)) — tempo/transport, injecting exported grooves into clip slots, launching clips, synth parameter editing, preset browsing, and a measured capture-and-tune loop (`hear.py` measures timbre, width and sidechain pump). See [`osc-protocol.md`](skills/bitwig-control/references/osc-protocol.md) and, before trusting any address, [`verified-behaviors.md`](skills/bitwig-control/references/verified-behaviors.md) — the evidence log of everything that has silently failed.
- **[`bitwig-devices`](skills/bitwig-devices/SKILL.md)** — the recipe library: per-device setup subdocuments (parameter maps, raw↔display anchors, GUI-only boundaries, verified presets), grown one device per session.
- **[`diva`](skills/diva/SKILL.md)** and **[`serum2`](skills/serum2/SKILL.md)** — dedicated synth skills (complex synths get their own): model-dependent controllable surfaces, manual-backed architecture maps, measured patch recipes. Serum is driven over MIDI CC, the only programmatic path it offers.
- **[`groove`](skills/groove/SKILL.md)** — why a pattern feels stiff, and which lever actually fixes it. Research-backed, adversarially verified. Its headline: in grid-quantized music the fix is almost always a *sound* lever, not a timing one.

Together they close the loop: analyze a reference → extract numeric targets → recreate it in Bitwig → capture and converge until the measurements agree.

The governing rule is **measure, don't guess** — every expensive mistake in this repo's history was a plausible guess a cheap measurement would have killed. [`CLAUDE.md`](CLAUDE.md) is the orientation for agents working *on* this repo.

Scope: steady-tempo 4/4 electronic music (techno, house, psy, and neighbors).
