# Sampler (Bitwig native, incl. inside Drum Machine pads)

Remote-control pages (enumerated live 2026-07-20 on a pad's Sampler):

| page | params 1-8 |
|---|---|
| Overview | Select · Mode · Filt Freq · Filt Reso · Vel Sens. · Gain · Pan · Output |
| Perform | Speed · Pitch · Start Pos · Freeze · Formant · Grain · Loop St. · Loop Len |
| Amp EG | Attack · Decay · Sustain · Release · A Curve · D Curve · Hold · R Curve |

- Anchors: Decay raw 40 → 88.1 ms · 60 → 261 ms · 62 → 291 ms (log-ish curve).
- Tightening a boomy one-shot (kick body eating 60–120 Hz): shorten Amp EG
  Decay + Sustain 0 — but reaching a *specific pad's* Sampler needs the
  human to click that pad first (see the nested-cursor limit in
  bitwig-control/verified-behaviors.md).
