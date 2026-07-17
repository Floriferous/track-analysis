# Compressor+ (Bitwig native)

**What it's for**: the workhorse compressor; here mainly kick-keyed sidechain
pump on bass/pads. Fully OSC-tunable — all calibration knobs on one page.

## Insert

Native device, reachable in the browser insertion flow (alphabetical device
list: sorts right after Chorus+, before Compressor). On a busy chain the
user dragging it is faster; on an empty instrument track the contextual
browser flow works (see bitwig-control).

## Pages & params

Remote-control pages: **Primary**, GR, Color, Bands. Everything needed for
sidechain work is on **Primary**:

| # | name | anchors (raw/127 → display) |
|---|---|---|
| 1 | Threshold | 32→−35.9 dB · 56→−26.8 · 64→−23.8 · 70→−21.5 · 74→−20.0 · 79→−18.1 · 89→−14.4 · default −12.0 |
| 2 | Ratio | 83→1:2.89 · 108→1:6.68 · 127→1:∞ · default 1:2 |
| 3 | Attack | 13→0.64 ms · 28→6.35 ms · default 24.4 ms |
| 4 | Release | 41→73.9 ms · 57→199 ms · 64→281 ms · default 125 ms |
| 5 | Mode (Vanilla/…) | 6 Auto Timing · 7 VCA Color · 8 Make-up |

Threshold is roughly linear at ~0.5 dB per raw step around the working range;
interpolate between anchors rather than searching.

## GUI-only

- **Sidechain key input** — the chooser in the device's expanded panel.
  Ask for the exact source: *"key input → Tracks → <track> → <container> →
  <pad/chain> (POST)"*. For kick-keyed pump, key from the **kick pad's
  chain (POST)**, never the whole drum track (hats would duck the offbeats).
- Sidechain FX tab (filters on the key) — GUI-only, rarely needed.

## Presets

### `sidechain-pump` — reference-grade kick duck (calibrated 2026-07-12)

Modeled on Bruno (HU) "Pyrodoxine" (deep-pass target: duck ~99%, minimum at
17% of beat, fully recovered by 3/4).

| param | raw | display |
|---|---|---|
| Threshold | 56 | −26.8 dB |
| Ratio | 127 | 1:∞ |
| Attack | 13 | 0.64 ms |
| Release | 57 | 199 ms (at 130.4 BPM — keep **release ≈ 0.43 × beat length** at other tempos) |

Key: kick pad chain (POST). Measured result, isolated bass at 130.4 BPM:
**duck 93%, minimum at 15% of beat, 92% recovered at 3/4** — within a few
points of the reference on all three.

Verify with the bitwig-control tweak loop:
`capture.py --scene <held-bass scene> --bars 2 --pump --pump-band 120,300`,
with the **key-source track muted** (isolates the pumped signal; the
container-internal key tap survives track mute — soloing instead kills the
key). Expect the three numbers above ±5.

Depth trades against threshold: −20 dB ≈ 84% duck, −24 ≈ 88%, −27 ≈ 93%
(ratio 1:∞, this key level — a hotter/quieter kick shifts the whole scale;
trust the measurement, not the absolute dB).
