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
- Sidechain (added 2026-07-17): Compressor+ after Serum, keyed from the
  kick pad chain (POST), `sidechain-pump` recalibrated values — Threshold
  raw 28 (−37.4 dB), Ratio 127 (1:∞), Attack 13 (0.64 ms), Release 50
  (134 ms). Measured under kick: pump **98.0 / 12.5 / 100** (duck / min-at
  / recovery-3/4) vs reference 99/17/100, timbre unchanged (44.0/27.7/28.2).
- Vs the Diva version (diva/references/patches.md): this patch is *static*
  — repeat captures agree within ~1 point, where Diva's feedback/VCO-beat
  swings ±4–10. Use Serum when the reference profile must be hit exactly;
  Diva for analog movement.
- Still open: level balance vs kick in the full mix (patch RMS −33 dBFS is
  quiet — raise track volume, not drive).
- 2026-07-20 replay on a rebuilt instance (fresh Init + re-learned roster,
  IAC transport): first take 43.1/32.0/24.1 but RMS −21.5 (11 dB hotter)
  and f0 −23c vs +12c — the rebuilt Init state differs from the banked one
  in level/tuning. Re-converge briefly before precision work; the CC state
  above remains the right starting point.
