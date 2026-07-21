---
name: groove
description: Why a programmed pattern feels stiff, robotic, mechanical, boring or lifeless — and which lever actually fixes it. Research-backed groove principles for grid-quantized electronic music: microtiming, swing, velocity, sidechain shape, humanization. Use when a loop is technically correct but does not feel good, before reaching for timing nudges or randomization.
---

# Groove

A pattern that measures right and still feels dead is the most common
failure in this repo's work. The instinct is to reach for timing —
humanize, swing, nudge. **The research says that instinct is usually
wrong**, and acting on it makes things worse.

## The headline

In grid-quantized electronic music, groove does **not** require onset
microtiming. Perceived timing shifts with a hit's attack shape, duration,
envelope, timbre and relative intensity — so the levers that create feel are
*sound* levers, not position levers. A sidechain's attack and release
literally change perceived timing without moving a single note.

**So when a pattern feels robotic, reach for sample choice, decay,
transient, stereo width, variation and pump shape first.** Timing is the
last resort, not the first.

This is not theory-for-its-own-sake: every "it sounds boring" moment in this
project has been fixed by a sound lever — a hat's variation and width, a
pad's chorus, a kick's body — and never by moving notes.

## Using this

1. **Name the complaint precisely.** "Boring" is not actionable; "the
   offbeats don't pull" and "every hat is identical" are. Measure before
   believing it: a part that sounds small is often mono
   (`hear.py --width`), not dull.
2. **Pick the lever from `references/principles.md`**, which is ordered by
   verified impact and states what backfires. Read it before changing
   anything — several plausible moves (randomizing timing, exaggerating
   deviations) are measurably counterproductive.
3. **Change one lever, then listen.** Groove claims are perceptual; the
   capture loop can tell you a hat got wider or a duck got deeper, it cannot
   tell you the loop feels better. The user's ears are the judge.

## Trust

`references/principles.md` is v2, rebuilt from a deep-research pass: 22
sources, 24 claims surviving 3-vote adversarial verification, each tagged
with its support. `references/sources.md` holds the citations. Claims are
labelled by strength — peer-reviewed findings, practitioner consensus, and
single-source assertions are not the same thing, and the file says which is
which. Promote what survives listening; delete what doesn't.

## Files

- `references/principles.md` — the levers, ordered by verified impact, with
  the backfires called out.
- `references/sources.md` — citations and how each claim was verified.
