---
name: diva
description: Sound-design on u-he Diva inside Bitwig — enumerating the patch's controllable surface, mapping it to Diva's panel/model architecture, and tuning patches by measurement. Use when a task names Diva — tweaking or building a Diva patch, fattening/brightening a Diva bass, choosing between its oscillator or filter models, or interpreting Diva parameters seen in Bitwig.
---

# Diva

Diva is a panels-with-swappable-models analog emulation; what Bitwig exposes
over OSC is a *projection of the current preset's active models*, so the
controllable surface must be discovered per patch, never assumed. Mechanics
(param writes, capture loop) come from `bitwig-control`; recipes for other
devices from `bitwig-devices`; this skill is the Diva-specific knowledge.

## Steps

1. **Pin and enumerate.** Cursor on Diva, `raw /device/pinned 1`, then
   `bw.py pages` — the full page/param inventory for *this* patch. Done when
   you hold the JSON and know which panels (osc model, filter model, envs,
   effects) the patch runs — `references/architecture.md` translates page
   names to panels, models, and manual pages.
2. **State the target as numbers.** A timbre goal becomes a hear.py profile
   (fundamental, harmonic ladder, band shares — from a reference stem or the
   user's description); movement/pump goals become curve metrics. No target,
   no tweaking.
3. **Tweak by the semantics, verify by the loop.** Pick knobs from the
   architecture doc's semantics table (harmonics → `Feedback`, `FilterFM`,
   filter `Frequency`; movement → `FreqModDepth`/`ModEnv`; width of analog
   character → osc tuning/PW), write with `bw.py param`, measure each move
   with the `bitwig-control` tweak loop. A knob whose write reads `[OK]` but
   whose spectrum doesn't move belongs to an inactive model — pick another.
   For controls not in the pages: the user clicks it in Diva's UI, you drive
   `raw /device/lastparam/value`.
4. **Bank the result.** A patch worth keeping gets an entry in
   `references/patches.md`: page/param/raw values actually set, the measured
   profile, and the preset it started from. Done when a fresh session could
   reproduce the sound from the entry alone.

## Diva-specific facts that bite

- **Sounding pitch may be transposed from written pitch** (3EE packs run
  −12): verify the sounding fundamental with the hearing loop before
  trusting MIDI; fix octave mismatches in the MIDI clip, not the patch.
- **Some params are bipolar with raw 64 ≈ 0** (FilterFM measured): read the
  display's sign around center before sweeping, or a "reduction" turns the
  knob off entirely.
- **Patches breathe**: detuned-VCO beating swings band shares ±10 points
  across captures (measured at OscMix < 100). Capture ≥8 bars and trust
  only the tweak loop's twice-in-a-row criterion.
- Preset loading over OSC works (browser preset flow, Category filter), and
  the pages change with the preset — re-enumerate after every load.
- CPU: Diva is expensive; if the engine chokes during captures, ask the user
  to check Diva's Accuracy setting (GUI-only).

## Files

- `references/architecture.md` — page names ↔ panels/models ↔ manual pages,
  param semantics, live-verified working notes. Start here every session.
- `references/Diva-user-guide.pdf` — the official manual (v1.4.8); read the
  cited pages when a model's behavior matters (e.g. filter model choice).
- `references/patches.md` — banked patch recipes with measured profiles.
