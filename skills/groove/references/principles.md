# Groove principles — distilled for programming, not reading

Distilled 2026-07-21 from the sources in `sources.md`, ordered by impact
(Roger Linn's ranking, confirmed by the Danielsen EDM interviews). These are
the rules the next drum pass gets built from; promote what survives
listening into a skill, delete what doesn't.

## 0. Beat design beats everything

"All the swing, dynamics and other tricks won't do you any good unless you
come up with a good beat" (Linn). A robotic loop is usually a *design*
problem first: every element playing every bar, no call-and-response, no
phrase shape. Sparse syncopated elements that appear every 2–4 bars (a
conga pair, a tom answer, one clap at the phrase end) do more than any
humanizer.

## 1. Swing, not randomness

- Swing = delaying the even-numbered 16ths only. 50% straight · 54% barely
  loose (doesn't read as swing) · 56–58% clearly groovy · 66% triplet.
  Genre homes: melodic techno ~10% Maschine-style (≈54–55%), nu-disco/indie
  50–60%, psy mostly straight (the rush comes from velocity cycling).
- **Random microtiming is measurably worse than the grid** (Frühauf):
  never `humanize-randomize` timing. EDM is tight; deviations are
  *deliberate and per-element*, milliseconds scale:
  - nudge a repeated colour element (rim/shaker) slightly off the kick's
    transient to separate them;
  - push/pull ONE element consistently (upper-register perc pushes, low
    stays anchored — the balanço register rule);
  - or shift a whole section a few ms (track-delay move) for mood.

## 2. Velocity architecture (the "breathing")

Structured, cyclic, never flat and never random:
- 16th-note motion layers cycle a fixed ladder — psy closed hats
  **67/48/99/48** (53/38/78/38% of 127), accent landing OFF the kick;
  melodic-techno maracas similar with softer spread.
- Keep continuous layers inside a narrow band (±5–10 MIDI) and use accents
  to "create and dispel momentum" — crescendo into a downbeat, duck after.
- Ghost hits (kick or snare at ~35–45 velocity) in the gaps: felt, not heard.
- Sidechain is part of the dynamic groove: low ratio (~1.2:1) = drive
  without seasick pumping; deep ratios only for the pump-as-feature drops.

## 3. Sound choice IS microrhythm (the EDM-specific truth)

Producers shape groove by shaping sounds, not sliding notes:
- **Attack shape**: sharp attack reads as pushed/"on", soft attack reads
  laid-back — choose/shape per role before touching timing.
- **Duration**: vary hat note lengths with (or against) the velocity
  pattern; louder=longer mirrors a real player. Choked/gated tails groove.
- **Fake round-robin**: 3–5 copies of one hat/perc sample pitched ±15–30
  cents, alternated per step — kills the machine-gun effect at the source.
- **Tune the kit**: kick pitched to the track key; perc tuned to chord
  tones (the Attack melodic-techno kit tunes everything to E).
- A kick a few semitones lower = heavier/laid-back mood without moving it.

## 4. Space is a groove element

Dry-and-loud everywhere = robotic even with perfect swing. The recipes all
lean on: clap/snare drowned in a big reverb but filtered low, perc accents
with plate tails, delay throws at phrase ends, one element panned off-center
(psy hats ~20%), auto-pan on the 16th motion layer. The silence between
drop hits is part of the pattern.

## 5. Genre placement cheat-sheet

- **Melodic techno (120–124)**: 4-floor tuned kick (short!); offbeat hat
  layer + a second dynamic hat; 16th maracas/shaker as motion; clap only at
  2–4 bar phrase ends (reverbed); syncopated tuned conga/tom every 2 bars;
  rim on upbeats nudged; ~10% swing.
- **Psytrance (138–145, ours 130)**: 4-floor kick; closed hats every 16th
  with the 53/38/78/38 cycle; open hats between kicks (velocity-alternating);
  claps with kicks 2+4; bass owns the 8th offbeats; straight grid, groove
  entirely from velocity cycling + bass/kick call-response.
- **Indie dance / nu-disco (110–120)**: kicks 1+3 (or lazy 4-floor);
  layered claps+snare on 2+4, each offset a little; 8th hats with drawn
  velocity arcs; ghost snare before bar ends; low shaker glue; pitched
  bongo/cowbell one-shots; swing 50–60%.

## 6. Steal the groove from the reference (our unfair advantage)

The dossier's window analysis already measures the real track's onsets:
`grid16` position, `offset_ms`, normalized `vel` per band. That is a groove
template. Procedure: read the drop window's hat/perc band onsets → build
the velocity ladder and the per-position ms offsets from what's measured →
program *the reference's* groove, not a textbook's. (Pyrodoxine's drop
shows systematic +40 ms pushes on some offbeats and a 0.5–1.0 vel ladder —
none of which our first robotic pass used.)
