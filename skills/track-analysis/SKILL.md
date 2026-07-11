---
name: track-analysis
description: Analyze an electronic-music audio file (WAV/MP3/AIFF/FLAC) into timestamped, discussable artifacts — BPM, beat/bar grid, arrangement map, drum-pattern grids, spectrograms, loudness, plus a stem-level deep pass for groove, bass placement, and sound design. Use when the user shares an audio track, asks what sounds or patterns occur at a timestamp, asks about a track's structure, groove, bass line, sound design, or loudness, wants tracks (or a work-in-progress vs references) compared, or wants a groove exported as MIDI.
---

# Track Analysis

You cannot hear audio. A **dossier** — spectrogram images, timestamped JSON, pattern grids — is how a track becomes something you can reason over. Scope: steady-tempo 4/4 electronic music (techno, house, psy, and neighbors); the beat, bar, and kick-anchor logic assumes it. Formats: whatever libsndfile decodes — WAV, MP3, AIFF, FLAC, OGG.

Required inputs: a track, and **one or more analysis windows** for any detailed (grid/spectrogram) work. There are no default windows — a timestamp chosen without seeing the arrangement lands in fills and breakdowns. Windows come from the user's timestamps, or from `overview.png` (step 2).

Two passes, by depth of question:

- **Light pass** (`ingest.py`) — whole track, under a minute: tempo, beat/bar grid, arrangement map, per-window drum grids and spectrograms, LUFS/dynamics, key. Always start here.
- **Deep pass** (`deep.py`) — one 60–120s groove slice, needs CPU torch + Demucs (~1–2 min): stems, kick anatomy, sidechain pump, hat accent contour, stereo width, cross-element microtiming, bass-note placement. Reach for it when the conversation turns to groove construction, note placement, sound design, or mix decisions.

## Steps

1. **Set up.** Work in a virtualenv on Python 3.11–3.12 (essentia and torch wheels lag the newest Python; on 3.13+ expect missing wheels) — `uv venv --python 3.12 .venv` or `python3.12 -m venv .venv`, then install with that interpreter. `pip install librosa soundfile matplotlib scipy` (core), plus the enrichers `pip install pretty_midi pyloudnorm essentia "beat_this @ git+https://github.com/CPJKU/beat_this.git"` — the passes degrade gracefully when an enricher is missing (Beat This! upgrades the grid, Essentia the key, pyloudnorm adds loudness); `pretty_midi` is a hard requirement of `midi.py` only. Deep pass additionally: `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu` then `pip install demucs` (keep torch and torchaudio on matching CPU builds — mixing with PyPI CUDA wheels breaks imports). Done when `python -c "import librosa, soundfile"` (plus `import torch, demucs` for deep) succeeds.
2. **Light pass.** `python scripts/ingest.py <audio> --windows <t1,t2,...> --out <dir>` with windows at the timestamps under discussion (`M:SS` or seconds). No timestamps under discussion yet → run once *without* `--windows` (whole-track outputs only), look at `overview.png`, and rerun with windows placed in the sections that matter — the main groove, a drop, wherever the question points; window reruns merge into the existing `dossier.json`. Done when the track folder holds `dossier.json`, `overview.png`, and one `spec_*.png` per window.
3. **Deep pass** (when warranted). Pick a groove-representative slice from `overview.png` — main groove, not intro or breakdown — and run `python scripts/deep.py <audio> --start <M:SS> --end <M:SS> --out <dir>`. Done when the slice folder holds `deep.json`, `anatomy.png`, and `stems.png`.
4. **Look at every image.** Read each artifact with your vision — images carry what the JSON can't: filter sweeps, reverb tails, texture changes, layering, pitch-drop kick tails, per-note harmonic movement in the bass stem. Done when every drum grid has been cross-checked against its spectrogram; a grid that contradicts its spectrogram is a detection failure, not a musical fact (failure modes and how to read each artifact: `references/dossier-format.md`). Fastest tell: a sub/kick row with offset sd ≳ 15 ms while the other bands sit at 5–7 ms means a rolling bassline is polluting the kick band (failure mode 2) — trust the spectrogram, or resolve with the deep pass's stems.
5. **Answer in musical time.** Convert user timestamps to bars via `bar_starts` in `dossier.json`; quote patterns in grid notation with bar numbers and clock time; render bass placement as a groove blueprint (kick/bass/hats rows against 16th positions). A question about an uncovered timestamp → rerun step 2 or 3 for it. Done when every claim is backed by a named artifact and carries its trust level below.

## Tools on demand

- **Compare** — `python scripts/compare.py <a>/deep.json <b>/deep.json` prints the producer's A/B table: duck depth, pump/hat-contour correlations, width per band, bass density/duration spread/on-kick share. The core of the reference workflow: analyze the user's own draft with the same pipeline, then diff it against their references — every session ends with a quantified gap list, not vibes.
- **MIDI export** — `python scripts/midi.py --deep <deep.json> [--dossier <dossier.json> --window <label>] --out <dir>` writes the bass blueprint and/or a drum groove as `.mid` to drag into a DAW (correct BPM; drum hits keep measured velocities and micro-offsets, bass notes keep placement and length). Offer it whenever a groove has been analyzed — playing inside a groove teaches more than reading about it.

## Trust boundaries

- **Solid**: BPM, beat stability, pattern grids (after the step-4 cross-check), arrangement boundaries, LUFS/crest/dynamics, key when Essentia and the transcribed bass root agree, bass-note placement and lengths (note *class* — see weak for octave), kick f0 glide, pump depth and shape, stereo width per band, within-band timing spread (sd < 5 ms ⇒ fully quantized) and within-band *relative* offsets (e.g. lead-in 16ths landing late relative to accented hits), and *differential* comparisons of the same measurement across tracks.
- **Weak**: key from the chroma fallback (always labeled "weak" in the output — report the relative major/minor ambiguity), pYIN octave (36 Hz vs 72 Hz confusions), section *labels* (the tool finds boundaries, not meanings), the "other" stem (carries separation bleed).
- **Artifact — never report as groove**: cross-element absolute timing offsets (mechanism: failure mode 3 in `references/dossier-format.md`). A kick reading late vs its hats is indistinguishable from a slow-blooming kick transient without waveform-level inspection; if it matters, say so instead of picking one.

## Files

- `scripts/ingest.py` — light pass; band ranges and detection parameters at the top.
- `scripts/deep.py` — deep pass; stems are cached in the output folder, so re-runs are cheap.
- `scripts/compare.py`, `scripts/midi.py` — the on-demand tools above.
- `scripts/common.py` — shared beat/bar grid (Beat This! when installed, kick-anchored librosa fallback; `grid_source` in every JSON says which ran).
- `references/dossier-format.md` — output schemas, grid notation, artifact interpretation, known failure modes.
- `references/sources.md` — the research behind the design: tools, papers, and upgrade paths.
