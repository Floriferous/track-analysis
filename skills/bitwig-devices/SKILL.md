---
name: bitwig-devices
description: Setup recipes for specific Bitwig devices and plugins — insertion, parameter maps with raw↔display anchor values, GUI-only boundaries, and verified named presets. Use when setting up, inserting, or configuring a named device (Compressor+ sidechain, a synth patch, an EQ), or when a device setup just succeeded and its recipe should be recorded.
---

# Bitwig Device Recipes

A recipe turns "figure this device out" into "apply what we already learned."
One subdocument per device in `devices/`; mechanics (param writes, capture
loop, browser insertion, sidechain physics) live in the `bitwig-control`
skill — recipes hold only what is specific to the device.

## Using a recipe

1. Named device → open `devices/<device>.md` (index below). Follow its
   parameter map and named presets instead of rediscovering them; its
   **anchor values** turn "set threshold to −27 dB" into one verified raw
   write instead of a search.
2. Done when the recipe's verification passes — each preset states its
   measured numbers and how to reproduce the measurement.

## Growing the library

A device set up without a recipe is a session that will be paid for twice.
After any from-scratch device setup: write `devices/<device>.md` before
moving on — the session already produced everything the recipe needs
(page/param layout from `params`, anchor values from the `[OK]` readbacks,
the GUI-only steps that had to be asked of the user, the final settings and
their measured result). Format, in order:

- **What it's for** — one line.
- **Insert** — how it lands on a track (browser flow, or "user drags it").
- **Pages & params** — page names; per page the 8 param names, with
  raw↔display anchor points actually observed.
- **GUI-only** — what OSC cannot reach on this device (routing choosers,
  curve editors); phrase as the exact click to ask of the user.
- **Presets** — named, purpose-tagged settings: raw values, resulting
  displays, the verification measurement and its numbers, tempo-dependent
  values expressed relative to the beat.

## Index

- [`devices/compressor-plus.md`](devices/compressor-plus.md) — Compressor+:
  sidechain pump (kick-keyed duck), the four-knob calibration map.
- [`devices/organ.md`](devices/organ.md) — Organ: drawbar map with dB
  anchors; `clean-sub` and `warm-stab` presets.
