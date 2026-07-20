#!/usr/bin/env python
"""Bind the standard Serum 2 CC roster via MIDI Learn, self-paced.

Run this in a terminal next to Serum's GUI. For each knob it names:
  1. In Serum: right-click the knob -> MIDI Learn (Serum now waits for a CC).
  2. Here: press Enter -> the script sends that knob's roster CC, completing
     the bind. The knob will visibly jump to mid-position (the CC value).
  s+Enter skips a knob (e.g. already bound), q+Enter quits.

Prerequisite: the track holding Serum must be record-armed (the script arms
BITWIG_SERUM_TRACK, default 4) — vkb_midi CC only reaches armed/monitoring
tracks.

Afterwards, in Serum's main menu: Save MIDI Map -> save as
  default.SerumMIDIMap
in  Serum 2 Presets/System/MIDI CC Maps/  (overwrite). Every new Serum
instance then loads the roster automatically (manual p27).
"""

import os
import time

import mido
from pythonosc.udp_client import SimpleUDPClient

HOST = os.environ.get("BITWIG_OSC_HOST", "127.0.0.1")
PORT = int(os.environ.get("BITWIG_OSC_SEND_PORT", "8000"))
TRACK = int(os.environ.get("BITWIG_SERUM_TRACK", "4"))
# CCs ride the IAC bus (Generic controller in Bitwig), NOT vkb_midi:
# DrivenByMoss's CC injection was observed to silently die (2026-07-20)
# while the IAC path is controller-independent.
MIDI_PORT = os.environ.get("CLAUDE_CC_PORT", "IAC Driver Bus 2")

# The standard roster, in MIDI "undefined" CC ranges (22-31, 85-89) so it
# never collides with mod wheel/volume/pan/sustain. CC 14-21 stay reserved
# for Macros 1-8 (factory map). Ground truth for what is actually bound is
# the decoded default.SerumMIDIMap (serumfile.py map); this table is the
# binding *procedure*, and control-surface.md carries the annotated result.
ROSTER = [
    (22, "FILTER 1 — Cutoff"),
    (23, "FILTER 1 — Resonance"),
    (24, "FILTER 1 — Drive"),
    (25, "FILTER 1 — Mix (dry/wet)"),
    (26, "OSC A — Level"),
    (27, "OSC A — WT Position"),
    (28, "OSC A — Unison Detune"),
    (29, "OSC A — Warp amount"),
    (30, "SUB — Level"),
    (31, "NOISE — Level"),
    (85, "ENV 1 — Attack"),
    (86, "ENV 1 — Decay"),
    (87, "ENV 1 — Sustain"),
    (89, "ENV 1 — Release"),
]


def main() -> None:
    client = SimpleUDPClient(HOST, PORT)
    client.send_message(f"/track/{TRACK}/recarm", 1)
    time.sleep(0.3)
    midi = mido.open_output(MIDI_PORT)
    print(f"OSC -> {HOST}:{PORT}, track {TRACK} armed; CCs -> {MIDI_PORT}.\n")

    def send(cc, value):
        midi.send(mido.Message("control_change", channel=0, control=cc,
                               value=value))
        time.sleep(0.15)

    for cc, knob in ROSTER:
        ans = input(f"[CC{cc}] Right-click {knob} -> MIDI Learn, then Enter "
                    "(s=skip, q=quit): ").strip().lower()
        if ans == "q":
            break
        if ans == "s":
            continue
        send(cc, 64)
        send(cc, 72)
        send(cc, 64)
        print(f"    sent CC{cc} — the {knob} knob should have jumped to ~50%.")
    midi.close()

    print("\nDone. Now in Serum's main menu: Save MIDI Map ->")
    print("  Serum 2 Presets/System/MIDI CC Maps/default.SerumMIDIMap  (overwrite)")
    print("Then tell the agent — it verifies the map file and the bindings by ear.")


if __name__ == "__main__":
    main()
