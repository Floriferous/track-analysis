# Organ (Bitwig native)

**What it's for**: drawbar organ; doubles as a quick clean sub-bass or warm
stab source when no dedicated synth is loaded.

## Insert

Native instrument, contextual browser flow works; user drag is fine.

## Pages & params

Page **Bars** (first page): 8 drawbars as dB gains, one param each —
1 Sub (−1 oct) · 2 5th · 3 Fund. · 4 8th (+1 oct) · 5 12th · 6 15th ·
7 17th · 8 19th. Anchors: raw 0 → −Inf dB · 44 → −27.6 · 70 → −15.5 ·
102 → −5.7 · 127 → 0.0 dB.

## GUI-only

Nothing needed for drawbar work; percussion/click controls untested.

## Presets

### `clean-sub` — mono sub bass (verified 2026-07-21, Beyond Gravity rebuild)

Fund. 127 (0 dB), 8th 44 (−27.6 dB, faint audibility octave), all other
bars 0 (−Inf). Note C♯1 → 35 Hz fundamental. NB the Sub drawbar is one
octave *below* the played note — off for sub-bass patches (C♯0 ≈ 17 Hz).
Verified by track VU while clip playing; no spectral capture yet.

### `warm-stab` — 200–400 Hz stab bed (same session)

Sub 0 · 5th 70 (−15.5) · Fund. 127 (0) · 8th 102 (−5.7) · 12th 57 (−20.9) ·
15th 38 (−31.4) · 17th/19th 0. Amplitude gating comes from short clip notes
(~0.3 beat); Organ itself has no envelope on this page.
