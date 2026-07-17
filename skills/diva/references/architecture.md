# Diva ↔ Bitwig: how the synth maps onto the controllable surface

Sources: the official manual in this folder (`Diva-user-guide.pdf`, v1.4.8 —
page numbers below cite it) and live OSC enumerations against **the CLAP
build** (`com.u-he.Diva`, verified in the project file) in Bitwig 5.3 — the
VST3 build's exposure is untested and may differ. Companion mechanics: the `bitwig-control` skill (`bw.py pages`, `param`,
tweak loop).

## The one fact that shapes everything

**Bitwig's remote-control pages for Diva are generated from the parameters
the current preset's active models publish** — different presets expose
different page sets. Observed live: a Digital-oscillator patch exposed pages
`VCO1/VCO2/VCO3/FM/Mod…`; a Dual VCO patch exposed
`VCO/TuneMod/PulsWdth/Sync/CrossMod/Mix/Feedback/Lowpass…`. Consequence:
**run `bw.py pages` after every preset load** — never assume yesterday's map.

## Diva's modular architecture (what the page names mean)

Diva is panels-with-swappable-models (manual p23):

| panel | models | manual | typical exposed pages |
|---|---|---|---|
| Oscillators | Triple VCO (p25) · Dual VCO (p26) · DCO (p28) · Dual VCO Eco · Digital (p29–30) | p23–31 | `VCO*`, `TuneMod`, `PulsWdth`, `Sync`, `CrossMod`, `Mix` |
| Center: Feedback / HPF | No-HPF-just-Feedback · 3 HPF models | p31 | `Feedback` |
| Main filter | Ladder (p33) · Cascade (p33) · Multimode (p34) · Bite (p35) · Uhbie (p36) | p32–36 | `Filter`, `Lowpass` (name follows model) |
| Envelopes ×2 | ADS · Analogue · Digital (ADSR variants) | p37–38 | `AmpEnv` (env1), `ModEnv` (env2) |
| LFOs ×2 | | p39 | `Vibrato`, mod-source fields |
| Effects ×2 | Chorus · Phaser · Plate · Delay · Rotary | p40–42 | `Plate2`, etc. (name = model + slot) |
| Voice / Tuning / Trimmers | | p43–47 | mostly not exposed |

## Sound-design semantics of the recurring exposed params

- **`Feedback`** (p31): post-filter signal fed back into the mixer — Diva's
  warmth/thickness/harmonics knob. First reach for fattening a bass.
- **`Frequency` / `Resonance`** on `Filter`/`Lowpass`: main filter cutoff
  (display ≈ semitone-ish units, ~30–150) and resonance.
- **`FreqModDepth` / `FreqMod2Depth`** (+ `…Src` fields): filter envelope /
  second-source modulation amounts — the "movement" controls.
- **`FilterFM`**: audio-rate filter FM from the oscillator — grit/growl.
- **`KeyFollow`**: cutoff tracks pitch; matters when a bassline spans octaves.
- **`OscMix`**: VCO1↔VCO2 balance (Dual VCO, p26; VCO1 carries the noise
  generator).
- **`Tune2`**: oscillator 2 tuning. **3EE preset-pack convention observed:
  patches sound −12 from written pitch** (Tune2 −12, or global transpose) —
  verify sounding octave with the hearing loop before trusting MIDI pitch.
- **`PulseWidth` / `PWModDepth`**, **`Sync2`**, **`FM`** (CrossMod): classic
  analog waveshaping — pulse width, hard sync, cross-modulation.
- **`AmpEnv`**: Attack/Decay/Sustain (+`Release On` toggle, Velocity,
  KeyFollow); **`ModEnv`** = envelope 2, the default filter-mod source.
- **`Vibrato`**: global pitch LFO amount.
- Displays mirror the GUI knob values — quote them back to the user in
  Diva's own units.

## Working notes (live-verified, with measured magnitudes)

- **`Feedback` is the dominant harmonics control** — measured on Pndrosa
  Beef (Dual VCO + Lowpass): 75→100 moved band shares from 92/5/3 to
  48/31/21 (sub/bass/low-mid) and H2 from −13 dB to −2.4 dB. One knob,
  half the timbre. Strongly nonlinear near the top of its range.
- **`FilterFM` is BIPOLAR and interacts multiplicatively with Feedback**:
  raw 64 ≈ display 0; the display curve is steep around center (raw 79 →
  +5.9, raw 92 → +10.8). Zeroing it collapsed the harmonic ladder even with
  Feedback at max (92/5/3, H2 −27) — at +6…+11 it trades bass-band into
  low-mid mildly. General rule: **check a param's display sign around raw 64
  before sweeping — assuming unipolar can turn a knob OFF that was
  load-bearing.**
- Params write like any Bitwig device (`bw.py param`, verify-retry
  included); a cold write occasionally needs the prime-with-current retry
  bw.py already performs.
- A parameter exposed on a page whose model is *inactive* silently does
  nothing to the sound (observed: `Shape1` writes on an unused oscillator
  path — `[OK]` readback, zero audible/measured change). The measured
  spectrum, not the readback, proves a knob is live.
- **Page navigation**: `bw.py pages` enumeration terminates on the first
  repeated page *name* (duplicate-named pages truncate it), and page-bank
  window names can read stale (`Rotary1/Plate2` appeared in a window whose
  other names were blank). Navigate by stepping `/device/param/+` and
  verifying `/device/page/selected/name` before every write.
- **Navigate pages by name — `bw.py page Lowpass` — never by index**
  (incident 2026-07-17: a numeric jump selected *Plate2* and two writes
  landed on the reverb's Wet; mechanism in bitwig-control's
  verified-behaviors.md). Diva has duplicate page names (two ModEnv, two
  Plate2 on Pndrosa Beef) — name navigation lands on the first match, so
  confirm with `params` that the params are the ones you expect.
- **Timbre is non-stationary when OscMix < 100** (Dual VCO): the two VCOs'
  detune beats on a tens-of-seconds period and band shares swing by ±10
  points between consecutive captures (measured: same knobs scored 1.6 and
  20.7 against a fixed target). Average ≥8 bars AND repeat the capture
  before trusting any number; a single great reading may be the beat's
  lucky phase. At OscMix = 100 variance drops to ±4.
- **Harmonic levers, measured** (Pndrosa Beef): `FilterFM`↑ feeds **H2**
  (bass band); **`OscMix` is the H3/low-mid lever** (90 vs 127 traded
  ~10 points of sub into bass+low-mid); `PulseWidth` and lowering filter
  `Frequency` both *reduced* upper harmonics here — the feedback path needs
  the filter open, so darkening the filter collapses the whole ladder
  rather than shaping it.
- Tuning fixes are usually better done in the MIDI (octave-transposed clips)
  than by hunting the patch's transpose — see the octave incident in
  `bitwig-control/references/verified-behaviors.md`.
