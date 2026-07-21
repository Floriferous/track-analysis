# Banked Diva patches

Each entry must let a fresh session reproduce the sound: starting preset,
every param actually changed (page / param # / raw value / display), and the
measured profile that defines "done".

## beyond-gravity-chords — converged (2026-07-21)

The melodic bed of Luis M "Beyond Gravity". **Target measured from the
Demucs `other` stem** (two 8 s windows) plus the exposed breakdown
(bars 83–95, no kick/bass):

- Band shares **low-mid 18.6–29.6 / mid 66.6–75.7 / high-mid 0.8–5.4 /
  high 0.1–0.3** — warm and filtered, nearly nothing above 2 kHz.
- Fundamentals **C♯4 (274–277 Hz)** and G♯3 (207 Hz).
- **Detuned**: peaks arrive in pairs 30–67 cents apart (406 *and* 422 Hz;
  274 *and* 282 Hz), matching the deep pass's 40–45% side energy.
- Harmony is C♯-rooted throughout, alternating **C♯–G♯–B** (adds ♭7) with
  **C♯–F♯–G♯** (sus4).

Recipe: preset **3EE_JP-G Ensemble** (Category=Pad), one change —
`Filter` 1 Frequency **73 → 62 (98.98 → 88.58)** to pull high-mid from
6.4% into range. **No transposition**: C♯4 written reads C♯4 sounding
(275.4 Hz), unlike the 3EE *bass* packs which run −12.
Converged captures: mid 73.7/75.3, high-mid 4.6/4.2, low-mid ~21/20.4.

**Analysis note that drove this**: the drum-grid rows looked nearly empty
across the breakdown windows, which reads as "nothing playing" but actually
means *sustained* material — onset detectors barely fire on held chords.
The spectrogram (continuous horizontal bands, chord changes every 1–2 bars)
is the artifact that tells the truth here, not the grid. An earlier pass
mistook this for quarter-note stabs and built a triad two octaves too low.

## beyond-gravity-bass — converged (2026-07-21)

Rolling sub modeled on Luis M "Beyond Gravity". **Target measured from the
Demucs bass stem** (`hear.py`, two consecutive 8 s windows agreeing):

- f0 **35.0 Hz = C♯1 +17c**; ladder confirmed by the full series
  35/70/105/140/175 (105 Hz rules out a 70 Hz fundamental, so this is *not*
  the pYIN octave trap).
- Levels: **H2 (70 Hz) 0 dB is the loudest partial**, H3 (105) −2.5,
  **H1 (35) −6…−8 (fundamental is BELOW H2)**, H4 (140) −15, H5 (175) −21.
- Band shares **sub 10–13 / bass 84–88 / low-mid 2.2–2.4**, and *literally
  zero* above 350 Hz. Contrast with pyrodoxine-bass (43/29/27): this is a
  far narrower sound, essentially H2+H3 only.

Key design consequence: the target needs a **rich ladder but a hard cliff**,
and on Pndrosa Beef those fight each other (the feedback path needs the
filter open — see architecture.md). Resolution used: build harmonics in
Diva, enforce the band limit **downstream with EQ+**, which is also what the
rolling-bass tutorials advise (synth for character, channel EQ for the
65–350 Hz window).

- Start: preset **3EE_Pndrosa Beef**, sounds −12 → MIDI clip plays C♯2
  (confirmed by capture: sounding f0 reads 35.2 Hz).
- Diva (page / param / raw → display):
  - `Mix` 5 Feedback → **127 → 100.00** (the single biggest lever: at raw 90
    the bass band was 10.7%, at 127 it jumped to 57.4%)
  - `Lowpass` 1 Frequency → **85 → 110.31** (open enough to keep the
    feedback path alive)
  - `Lowpass` 8 FilterFM → **92 → +10.77** (the H2 lever — do NOT zero it,
    that collapses the ladder to a dull 92/5/3 sub)
  - `Lowpass` 4 FreqModDepth → **64 → ~0** (kills Env2's per-note filter
    sweep; reference timbre is static note to note)
  - `AmpEnv` 2 Sustain → **127 → 100** with Decay 0: flat note, the
    sidechain does all the shaping
  - `Plate2` Wet → **0** (reverb on a sub is mud)
- **EQ+ after Diva does the band-shaping** (band / type / raw → display):
  - 1 **highcut** → 33 → **120 Hz** — the cliff above H3
  - 2 **lowcut** → 12 → **38.4 Hz** — pulls the fundamental under H2, which
    is what makes this bass read as "rolling" rather than "boomy"
  - 3 **bell** → freq 30 → 102 Hz, gain 80 → **+7.8 dB**, Q 100 → **8.33**
    — restores H3, which the 120 Hz highcut eats
- **Q must be narrow.** The same bell at default Q 1.00 lifted the whole
  70–140 region instead of H3 alone: H3 moved only 0.7 dB while H2 rose
  enough to push sub 14.0 → 6.1 and H1 to −11.5. At Q 8.33 it lifted H3 by
  5 dB and left H2/H4 alone. Wide-Q "surgical" boosts on a bass are a trap.
- Convergence path (band shares sub/bass/low-mid): Feedback 90 →
  **87/11/1** (a near-pure fundamental, no ladder) → Feedback 127 →
  ~37/57/5 → lowcut 60 Hz → 1.0/88.4/10.6 (overshot the bottom, fat top) →
  highcut 120 + lowcut 38 → 14.0/83.4/2.6 → narrow bell → **11.2/87.2/1.6
  and 9.6/88.1/2.3** on two consecutive captures vs target 10-13/84-88/2.2.
  Ladder landed H1 −6.3/−8.2, H3 −1.8/−2.7, H4 −18.0/−15.5 vs target
  −6…−8 / −2.5 / −15. Between-capture drift (±1.6 sub, ±2 dB H1) is the
  documented analog breathing — both takes straddled the target.
- Unreachable over OSC on this preset: `AmpEnv Attack` is absent from the
  live remote page (left at 13.00); needs the user's click +
  `/device/lastparam/value` if a snappier attack is ever wanted.

## pyrodoxine-bass — converged (2026-07-17)

Sub bass modeled on Bruno (HU) "Pyrodoxine" (reference stem profile:
f0 F1 ~43 Hz, band shares sub/bass/low-mid ≈ 43/29/27, H2/H3 strong).

- Start: preset **3EE_Pndrosa Beef** (Category=Bass in the preset browser).
  Dual VCO + Lowpass patch; sounds −12 from written pitch → **MIDI clips
  play +12** (F2 written = F1 sounding).
- Settings (page / param # / raw → display):
  - `Filter` (=Lowpass) 1 Frequency → **100 → 124.49** (wide open)
  - `Feedback` 1 Feedback → **127 → 100.00** (this knob did most of the work)
  - `Lowpass` 8 FilterFM → **92 → +10.77** (bipolar! raw 64 ≈ 0 — never
    "reduce" it below center by accident)
- Measured result (isolated, 130.4 BPM, hearing loop): f0 F1 ·
  **44.5/34.2/20.6** vs target 43/29/27 · H2 −1.6 dB.
  Convergence path: 92/5/3 → Feedback max → 48/31/21 → FilterFM +11 →
  44.5/34.2/20.6. Note rms rose ~4 dB with Feedback — rebalance track level
  after applying.
- Pairs with the Compressor+ `sidechain-pump` recipe (bitwig-devices) keyed
  from the kick pad — with the 2026-07-17 recalibration (Threshold 28,
  Release 40 for this bass's hot −21 dBFS RMS): measured pump
  **97.8 / 12.5 / 100** vs reference 99/17/100.
- 2026-07-17 comparison vs the Serum 2 version (serum2/references/
  patches.md): this patch's spectrum *breathes* — at OscMix 127 shares
  wander ±4 (39–49 sub), and OscMix 90 mixes in VCO2 for real H3 content
  (best single take 42.2/28.5/27.3) but beats on a ~15 s+ period, swinging
  ±10. The Serum version sits statically at 43.7/27.5/28.6. Pick by feel:
  Diva = living analog texture, Serum = surgical match. OscMix 90 is the
  documented alternative flavor; banked value stays 127.
