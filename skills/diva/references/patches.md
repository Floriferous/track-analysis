# Banked Diva patches

Each entry must let a fresh session reproduce the sound: starting preset,
every param actually changed (page / param # / raw value / display), and the
measured profile that defines "done".

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
  from the kick pad.
