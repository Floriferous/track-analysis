# Groove principles — distilled for programming, not reading

v2, 2026-07-21: rebuilt after the deep-research pass (22 sources, 24 claims
surviving 3-vote adversarial verification — see `sources.md`). Ordered by
verified impact. Promote what survives listening into a skill; delete what
doesn't.

## The headline (peer-reviewed, 3-0): groove without moving notes

In grid-quantized EDM, groove does NOT require onset microtiming. Sonic
features create an **"indirect microtiming"** effect — the perceived timing
of an on-grid hit shifts with its attack shape, duration, envelope, timbre,
and relative intensity (P-center research; Danielsen's five microrhythmic
parameters: *timing, duration, shape, timbre, relative intensity*).
Producers craft groove by shaping envelopes — a hat's attack rise, the
sidechain "breathing" — not by nudging events. **Sidechain attack/release
literally changes perceived timing** (Brøvig-Hanssen, MTO 2020): the pump
shape is a groove parameter tunable without touching MIDI.

Implication for us: when a pattern feels robotic, the next lever is usually
a *sound* lever (sample choice, decay, transient, pump shape, level), not a
timing lever.

## Timing: what's measured, what backfires

- Perception (Senn 2016, swing/funk stimuli): groove peaks around **60%
  reduction of natural microtiming** — quantized and naturally-loose both
  rate high, *exaggerated* deviations reliably rate worse. Never randomize;
  if borrowing a groove template, apply it at reduced depth (~40%).
- Swing (Linn, primary): useful range 50–~70%, **tempo-dependent** — a
  setting that grooves at 90 BPM fails at 125. 54% = loose-not-swung;
  58/62% = grooves a player couldn't perform. (Seeb use 22–40% Ableton
  swing — pop-EDM data point, 2-1 vote, not a genre norm.)
- Deliberate per-element nudges survive verification: rim/perc on upbeats
  pushed slightly EARLY specifically to clear the kick transient.
- Hardware "magic" is quantifiable and importable: MPC60/3000 = 96 PPQN
  coarseness, 808 clock jitter ±0.7%/measure; Grooves From Mars measured
  478 templates off 27 real machines — an option if we ever want machine
  feel without inventing it. Our own dossier extraction stays preferred
  (it measures the actual reference).

## The kick-bass engine (the richest verified area)

- **Tune the kick to the track** — Bieger calls it the single most
  important mixdown step. A kick pitched a few semitones down also reads
  heavier/more laid-back.
- **One voice, short sample**: kick sampler limited to 1 voice so tails
  never overlap; keep the kick short and snappy to leave the sub's room
  (psy rule of thumb: kick under ~130 ms at 145 BPM — scale ≈ under
  ~145 ms at our 130).
- **First 16th of each beat belongs to the kick**: rolling basslines leave
  it empty (our offbeat roll obeys this).
- **Spectral separation**: sub layer lowpassed ~80 Hz (12 dB/oct); kick gets
  a narrow bell cut (−1 to −4.5 dB) at the bass's root frequency, plus
  1–2 dB cuts at its key harmonics (psy practice). Kick sits **2–3 dB
  louder than the bass** (psy practice, unverified-tier but consistent).
- **Phase alignment** kick↔bass is taught as essential in psy schools
  (Zenon course); bass *tails* come from filter cutoff sitting above the
  fundamental so the low tone rings after the envelope closes.
- **Two sidechain schools**: psy practitioners preach gentle (2:1,
  threshold ≈ −20 dB, 3–6 dB GR — "space, not a substitute for sound
  design"); our band-limited reference measurement shows ~99% duck in
  120–300 Hz. Not necessarily contradictory (deep duck in a narrow band vs
  gentle broadband GR) — treat pump depth/shape as an aesthetic knob and
  judge by ear per track. Remember: the pump SHAPE is perceived timing.

## Dynamics and level (the "breathing")

- Velocity architecture: deep ghost/accent contrast (reference measured
  0.15 vs 0.94), cyclic ladders on 16th layers, accents that create and
  dispel momentum. (Beyond-accent phrase-level architecture went
  unverified — measure it ourselves, see agenda.)
- **Level balance is groove-critical: 2 dB in the wrong direction can
  "stagger the flow"** (Martinsen, interview study). Iterate element
  levels by measurement against the reference mix — small moves.

## Sound design of hats/perc

Two-layer hats (one anchoring, one *doubling* layer with reduced offbeat
velocity, shortened decay, HPF ~1.3 kHz, subtle modulation); fake
round-robin via 3–5 pitch-varied copies (±15–30 cents); duration variation
mirroring velocity; tune perc to the key (whole 808 kit tuned to E in the
Attack melodic-techno recipe).

## Space as rhythm

Rhythmic delays at musical subdivisions turn delay into a groove element —
verified dub recipe: rimshot send, 7/32 delay, ~100% regeneration, full
stereo width, filling the space *between* hits. Clap/snare drowned in a
big-but-filtered reverb; one motion layer auto-panned; psy hats ~20% off
center.

## Genre placement cheat-sheet (unchanged from v1)

- **Melodic techno (120–124)**: 4-floor tuned short kick; offbeat hat +
  doubling hat; 16th shaker motion; clap only at phrase ends (reverbed);
  sparse tuned conga/tom every 2 bars; rim upbeats nudged early; ~10%
  Maschine swing.
- **Psytrance (138–145, ours 130)**: straight grid; closed hats every 16th
  cycling 53/38/78/38%; open hats between kicks; bass owns the offbeat
  8ths; groove = velocity cycling + kick-bass call-response + pump shape.
- **Indie dance / nu-disco (110–120)**: kicks 1+3 or lazy 4-floor; layered
  claps/snare on 2+4 each offset differently; 8th hats with drawn velocity
  arcs; ghost snare before bar ends; swing 50–60%.

## Steal the groove from the reference (our unfair advantage)

The dossier windows measure the real track's onsets per grid16 with
`offset_ms` and normalized `vel` per band — a groove template of the actual
reference. Program *those* ladders and leads (at moderated depth per Senn).
Pyrodoxine drop, measured: hat ghost/accent 0.15/0.94; rolling bass leads
the kick band; pickup flams ~35 ms before downbeats; no clap layer.

## Measurement agenda (verified gaps → our tooling can answer)

The research could not verify: psy rolling-bass articulation (note lengths,
ghost notes, envelope), arrangement-level variation cadence (what actually
changes every 4/8/16 bars in released tracks), and phrase-level velocity
architecture. All three are *measurable from reference tracks with our own
analysis stack* — extract, don't speculate.
