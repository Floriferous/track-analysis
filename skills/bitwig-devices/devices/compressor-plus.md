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

### `sidechain-pump` — reference-grade kick duck (recalibrated 2026-07-17)

Modeled on Bruno (HU) "Pyrodoxine" (deep-pass target: duck ~99%, minimum at
17% of beat, fully recovered by 3/4).

| param | raw | display |
|---|---|---|
| Threshold | 28 | −37.4 dB |
| Ratio | 127 | 1:∞ |
| Attack | 13 | 0.64 ms |
| Release | 40–50 | 69–134 ms at 130.4 BPM — **tune by source level**, see below |

Key: kick pad chain (POST). Measured on two different basses at 130.4 BPM:
Serum (−35 RMS, release 50): **98.0 / 12.5 / 100**; Diva (−21 RMS, release
40): **97.8 / 12.5 / 100** (duck / min-at / recovered-at-3/4). The earlier
shallower calibration (Threshold 56, Release 57) measured 93/15/92 — keep
it only if a gentler pump is wanted.

**Release trades against source level**: a hotter signal sits deeper into
the compressor and climbs out slower — Diva at −21 RMS needed release 40
where Serum at −35 RMS recovered fully at 50. If recovery-at-3/4 reads low,
shorten release before touching threshold. Reminder: threshold *raw down =
dB down = deeper duck* (28→−37.4, 56→−26.8, 89→−14.4).

Verify with the bitwig-control tweak loop:
`capture.py --scene <held-bass scene> --bars 2 --pump --pump-band 120,300`,
with the **key-source track muted** (isolates the pumped signal; the
container-internal key tap survives track mute — soloing instead kills the
key). Expect the three numbers above ±5.

### `pump-medium` — 70% duck (Beyond Gravity, 2026-07-21)

Threshold **59 → −25.7 dB**, Ratio 1:∞, Attack 0.64 ms, Release 134 ms, key
from the kick *track* (POST). Measured **68–71% duck** on two consecutive
captures vs a 74% target, recovery 92–96% by 3/4.

Threshold→depth on this key level: −18.1 → **39%**, −23.8 → **68%**,
−25.7 → **68–71%**. Note how flat it goes past −24 — the last 3 dB of
threshold bought almost nothing, so chase depth with threshold only until
it plateaus.

**Measuring pump without solo**: soloing the pumped track kills the key, and
the kick pollutes any band it shares. Fix used here: capture the **full mix**
and band-limit to a band only the pumped signal occupies
(`--pump-band 350,2000` for a chord pad, where kick and bass both measured
0.0%). No mutes, no solos, no key loss.

**`minimum at X% of beat` is noisy — judge on depth.** Two back-to-back
captures of an unchanged patch gave min-at **12%** and **27%** (duck 71/68).
The trough is broad and flat, so the argmin wanders; the earlier pyrodoxine
entry's 12.5-vs-17 "offset" was probably this same noise, not a systematic
bias.

Depth trades against threshold: −20 dB ≈ 84% duck, −24 ≈ 88%, −27 ≈ 93%
(ratio 1:∞, this key level — a hotter/quieter kick shifts the whole scale;
trust the measurement, not the absolute dB).
