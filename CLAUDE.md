# track-analysis

Analyse electronic music tracks into numbers, then recreate them in Bitwig
Studio over OSC. Two halves of one loop:

    reference audio ──▶ targets.py ──▶ numeric target sheet
                                            │
                            build in Bitwig ▼
                        capture.py ──▶ measured ──▶ converge

## Setup

Use the repo venv — `.venv/bin/python`. Never the system interpreter:
essentia, torch and demucs are installed here and nowhere else.

## The skills are SOURCE here, not installed

`skills/` is what this repo *ships*. In this working copy they are **not**
auto-invocable — `Skill(bitwig-control)` fails. **Read `skills/<name>/SKILL.md`
directly** before doing anything in that area; each one links its own
references. They are worth reading in full, not skimming:

| skill | read it before |
|---|---|
| `track-analysis` | analysing audio, dossiers, stems, MIDI export |
| `bitwig-control` | any OSC/DAW work — **`references/verified-behaviors.md` is the trap list** |
| `bitwig-devices` | setting up a named device (parameter maps, calibrated presets) |
| `diva`, `serum2` | those synths specifically |
| `groove` | why a pattern feels robotic, before you touch timing |

## The one rule: measure, don't guess

Every expensive mistake in this project's history was a plausible guess that
a cheap measurement would have killed — a "four-on-the-floor" kick lane
exported with no note on beat 1; a whole invented chord part that the record
does not contain; an hour lost assuming a drum kit was GM-mapped.

So: **start a recreation with `targets.py`**, converge against those numbers
with `capture.py`, and treat two consecutive in-tolerance captures as done
(patches drift; one match can be luck).

Corollaries that keep biting:

- **A target you cannot measure identically on both sides is not a target.**
  The two halves of this repo use the same band names for different
  frequencies, and the pump duck uses different normalisation. `targets.py`
  converts; hand-copying a number between tools does not.
- **Isolate one variable per probe.** A device A/B identifies the device, not
  the note. A solo capture compared against a mixed stem proves nothing.
  Measure in a band the source actually owns.
- **A metric is only valid if the thing you are measuring is what moves it.**
  A duck figure read off a bus whose patch has its own per-bar envelope is
  that envelope, not the sidechain.
- **When something sounds small or boring, suspect the sound, not the
  timing** — width, decay, variation. See `skills/groove`. Nearly every fix
  in this repo's history has been a sound lever.

## OSC gotchas that cost real time

Full list in `skills/bitwig-control/references/verified-behaviors.md`; the
three that bite first:

- Bitwig sends **no error replies**. A failed write is silent and looks
  exactly like success — always read back.
- Continuous writes need **priming**; `bw.py` does it, other routes must.
- The GUI user **shares the cursor**. Pin the device, verify `/device/name`
  after asking for a click.

## Outputs are disposable

`dossier/`, `deep/`, `midi/`, `stems/` and all audio are gitignored — derived
data, regenerate rather than preserve. Only `skills/` and the docs are
tracked. Bitwig projects live outside this repo entirely
(`~/Documents/Bitwig Studio/Projects/`).
