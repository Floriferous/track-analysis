# Banked Serum 2 patches

Each entry must let a fresh session reproduce the sound: starting point,
every roster CC actually set, and the measured profile that defines "done".
CC values are 0–127 sent via `/vkb_midi/1/cc/{cc}` (roster in SKILL.md).

## pyrodoxine-bass2 — converged (2026-07-17)

Sub bass modeled on Bruno (HU) "Pyrodoxine" (target: f0 F1 ~43 Hz, band
shares sub/bass/low-mid ≈ 43/29/27, strong H2/H3). Companion to the Diva
version in `skills/diva/references/patches.md` (this one measured closer).

- Start: **Init patch** (OSC A saw = WT position 0, Filter 1 on, routed).
- Roster CCs (full state, order irrelevant):
  `22:48 (cutoff) · 23:45 (res) · 24:0 · 25:127 · 26:100 · 27:0 · 29:64 ·
  30:0 · 31:0 · 85:0 · 86:80 · 87:127 · 89:20`
- Measured (isolated, 130.4 BPM, held F2 → sounds F1): **43.7/27.5/28.6**,
  H2 −2.2 dB, H3 −3.4 dB, RMS −33.2 dBFS (quiet — raise track volume, not
  drive, when mixing).
- Convergence path (3 sweeps, 16 captures): WT position — saw frame 0 beat
  all others (32≈sine kills H2, 64≈triangle odd-only); cutoff down from
  open 100 into the H2–H4 region did the real work (52→48 with res 45);
  res above ~50 overshoots low-mid; drive 25–45 added +6–10 dB RMS but
  bent shares off target → left at 0.
- Not yet in the recipe: sidechain pump (Compressor+ `sidechain-pump` from
  `bitwig-devices`, keyed off the kick pad) and level balance vs kick.
