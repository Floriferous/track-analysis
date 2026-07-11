# Output formats, interpretation, and known failure modes

## Light pass (`ingest.py`) — per track: `<out>/<audio-file-stem>/`

- `dossier.json` — machine-readable summary (schema below)
- `overview.png` — band energy per bar for the whole track, section boundaries as cyan lines. The highest value-per-compute artifact: the track's whole dramaturgy in one image. Rows are the five analysis bands; brightness = energy normalized per band. Also the map for choosing a deep-pass slice.
- `spec_<label>.png` — mel spectrogram of each 4-bar analysis window (log-frequency to 16 kHz, beat positions as faint cyan lines)

### dossier.json schema

```
slug          str    track identifier (audio file stem)
duration_sec  float
bpm           float  global tempo estimate
key           str    "D minor (essentia 0.87)" or "... (chroma r=0.53, weak)" per available backend
grid_source   str    "beat_this" (model beats+downbeats) or "librosa+kick-anchor" (heuristic)
loudness      {integrated_lufs, short_term_max_lufs, short_term_range_lu,
               sample_peak_dbfs, crest_db} | null when pyloudnorm absent
n_bars        int
bar_starts    [float]  start time (sec) of every bar — THE timestamp↔bar converter
boundaries    [{bar, time}]  detected section changes
windows       {label: {t0, t1, bar, grids}}  per-window drum grids
```

Reruns with new `--windows` merge into an existing `dossier.json` (same label = overwritten), so a dossier accumulates windows across a conversation; whole-track fields reflect the latest run. Without `--windows` only the whole-track outputs are produced.

Loudness reading: modern club masters commonly sit around −8 to −10 LUFS integrated with crest ~9–11 dB; a much quieter or more dynamic reading is a mastering difference worth stating before comparing anything level-dependent.

Each `grids` entry maps a band name to hit lists: `{t, grid16, offset_ms, vel}` — absolute time, nearest 16th-note grid index within the window, signed offset from that grid position in ms, and normalized velocity (0–1, sqrt of band power relative to window peak).

## Deep pass (`deep.py`) — per slice: `<out>/<slug>_<start>-<end>/`

- `deep.json` — all numbers (schema below)
- `anatomy.png` — three panels: average kick waveform (lowpassed), kick f0 glide curve, sidechain pump over one beat
- `stems.png` — stacked mel spectrograms of the Demucs stems (drums / bass / other; vocals only when non-silent), 2 bars starting at the bass window
- `<slug>_<stem>.wav` — cached stems; re-runs skip separation

### deep.json schema

```
slug, t_start, t_end, bpm, grid_source
kick          {n, f0_start_hz, f0_end_hz, decay_ms|null} | absent when no kicks detected
pump          {duck_pct, min_at_beat_pct, curve[48]}  one folded beat, normalized
hat_contour   {vel[16], hits[16], offset_ms[16]}  per 16th position across all bars
stereo_width_side_share  {sub, bass, low-mid, mid, high}  0..1
microtiming   {element: {hits, mean_ms, sd_ms}}  onsets within ±45ms of the 16th grid
bass_notes    {bars: [b0, b1], notes: [{t, dur, hz, note, bar, pos16, dur16}]}
```

Bass notes and `stems.png` cover a 4-bar window away from the slice edges — bars 8–11 of the slice when it is long enough, clamped otherwise; the window actually used is recorded in `bass_notes.bars`. Slice something 60–120s so this window sits in the groove you care about.

### Reading the deep artifacts

- **Kick f0 glide**: start→end Hz of the sub fundamental over ~150 ms. Long smooth glide + blooming waveform = round sustained kick; fast glide to the floor = short kick that makes room. An f0 curve that *rises* again near the end means the bassline takes over the low end there — the kick/bass handoff, not part of the kick.
- **Sub decay** `null` means the low end never drops 20 dB within the analysis window — either a long kick tail or a bassline filling the inter-kick gap; the bass stem spectrogram tells you which.
- **Pump curve** (mid-band 300 Hz–6 kHz folded onto one beat): duck % = sidechain depth; where the minimum sits and how long the curve stays low = the compressor's hold/release shape; secondary humps = where offbeat elements carry the energy. Deep-and-long ducking is a *groove device* — it reserves the kick's slot; read it together with bass-note placement.
- **Hat accent contour**: mean velocity and hit count per 16th position across all bars. Shows the accent skeleton (beats vs offbeats vs lead-ins). The per-position mean offsets are within-band, so their *relative* differences are trustworthy — e.g. soft lead-in 16ths landing ~10 ms later than accented offbeats is a real drag/swing gesture.
- **Stereo width** (side share per band): sub and bass should read near 0% in club-ready mixes; where width appears above that is a mix decision worth reporting.
- **Cross-element microtiming**: within-element sd is the quantization verdict; means across elements carry band physics (see failure mode 3). Differential across tracks is meaningful.
- **Bass notes**: `{bar, pos16, dur16, note, hz}` per note. This is the note-placement blueprint: render it against kick positions as a groove diagram (which 16ths the bass owns, where it releases relative to the next kick). Regular pattern + identical durations = sequenced/locked; varying lengths and passing tones = performed/modulated line.

## Grid notation

The light pass prints (and you should quote) 4-bar step grids, one row per band, 16 sixteenths per bar between `|` marks:

- `X` — strong hit (vel > 0.75), `x` — medium (> 0.45), `o` — soft, `.` — nothing on that 16th
- Hits with |offset| ≥ 40 ms are dropped from the grid rendering (off-grid; inspect them in the JSON)
- Index 0 of each bar is the downbeat; indices 0/4/8/12 are the four beats; 2/6/10/14 are the offbeats ("and"s)

Reading examples: four-on-floor kick = `X...X...X...X...`; offbeat open hats = `..X...X...X...X.`; a rolling sub with a note on the 16th before each beat shows in the sub row as `X..xX..xX..xX..x`.

## Bands

Defined at the top of `ingest.py`: sub/kick 25–120 Hz, bass 120–350, low-mid 350–1k, mid 1k–4k, high/hats 6k–16k. The low-mid row frequently doubles the kick (its attack transient has mid-band energy) — corroborate against the sub row before calling something a separate percussion element.

## Known failure modes (all observed on real tracks)

1. **Offbeat phase lock** (librosa fallback grid only; `grid_source` says which ran). Beat trackers lock onto offbeat hats/bass instead of the kick — every grid then shows the kick at index 2 instead of 0. The fallback re-anchors beat phase to kick-band onset energy, but that correction itself fails on long kickless passages. Symptom: kick row pattern at indices 2/6/10/14. Fix: install Beat This!, re-run on a kick-present section, or distrust the phase.
2. **Sustained sub masks kick onsets.** Spectral-flux onset detection misses four-on-floor kicks riding on a continuous sub bassline. The scripts use amplitude-peak picking for the sub band instead — but on rolling-bass material (a large share of techno/house) the bassline still pollutes the sub grid: missing beats, spurious between-beat hits. The numeric tell: sub-band offset sd ≳ 15–20 ms while every other band sits at 5–7 ms; the spectrogram then typically shows clean kick attacks on every beat that the grid misses. The spectrogram cross-check (skill step 4) is the arbiter; the deep pass resolves it properly — its kick timing comes from the separated drums stem (~7 ms sd on material where the mixed sub band reads 20+ ms).
3. **Cross-band offset bias.** Low-frequency onsets smear late (long analysis windows), flux onsets fire at attack start — so absolute per-band offset means differ by ±30 ms for physical reasons, not musical ones. Persists even with one shared detector, because the bands themselves differ. Only within-band spread, within-band relative placement, and cross-track differentials are meaningful.
4. **Downbeat ambiguity** (librosa fallback grid only). Bar phase is a heuristic (strongest kick among the 4 beat phases); in music where every beat carries a kick, bars may be offset by 1–3 beats from the producer's intent. Beat This! predicts downbeats directly; boundaries and 16-bar phrasing hold relatively either way.
5. **Breakdown windows.** Inside kickless breakdowns the 16th grid is interpolated from surrounding beats and drifts; treat grids there as approximate and lean on the spectrogram. Same reason the deep-pass slice must be a groove section.
6. **Tempo octave errors.** Halved/doubled BPM is possible on sparse or very fast material; sanity-check against genre norms (techno 120–150, psytrance 138–148, DnB 170+).
7. **pYIN octave and bleed.** Bass notes can read an octave off (note class is reliable); kicks bleeding into the bass stem can add short spurious notes at kick positions — discount bass "notes" shorter than ~1 sixteenth that sit exactly on kicks.
