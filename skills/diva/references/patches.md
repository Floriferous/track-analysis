# Banked Diva patches

Each entry must let a fresh session reproduce the sound: starting preset,
every param actually changed (page / param # / raw value / display), and the
measured profile that defines "done".

## pyrodoxine-bass — WIP (2026-07-17)

Sub bass modeled on Bruno (HU) "Pyrodoxine" (reference stem profile:
f0 F1 ~43 Hz, band shares sub/bass/low-mid ≈ 43/29/27, harmonics H2/H3
strong).

- Start: preset **3EE_Pndrosa Beef** (Category=Bass filter in the browser).
  Dual VCO patch; sounds −12 from written pitch → **MIDI clips play +12**
  (F2 written = F1 sounding).
- Changed so far: `Filter` page param 1 Frequency → raw 100 (display
  124.49, wide open).
- Measured now: f0 43.9 Hz (F1 +12c) ✓ · harmonic ladder H2 −13 dB,
  H3 −16.5, H4 −24 · band shares **92/5/3** — harmonics still well short of
  the 43/29/27 target.
- Known live knobs for closing the gap (this patch's pages): `Feedback`
  (currently 75), `CrossMod FM`, `Mix OscMix` (100 = one osc only),
  `Lowpass FilterFM` (24). Next session: sweep Feedback and OscMix with the
  tweak loop against the band-share target.
- Context: pairs with the Compressor+ `sidechain-pump` recipe
  (bitwig-devices) keyed from the kick pad.
