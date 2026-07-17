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

from pythonosc.udp_client import SimpleUDPClient

HOST = os.environ.get("BITWIG_OSC_HOST", "127.0.0.1")
PORT = int(os.environ.get("BITWIG_OSC_SEND_PORT", "8000"))
TRACK = int(os.environ.get("BITWIG_SERUM_TRACK", "4"))
CHANNEL = 1

# The standard roster, in MIDI "undefined" CC ranges (22-31, 85-89) so it
# never collides with mod wheel/volume/pan/sustain. CC 14-21 stay reserved
# for Macros 1-8 (factory map). This table is the single source of truth —
# SKILL.md's roster table mirrors it.
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
    print(f"OSC -> {HOST}:{PORT}, track {TRACK} armed.\n")

    for cc, knob in ROSTER:
        ans = input(f"[CC{cc}] Right-click {knob} -> MIDI Learn, then Enter "
                    "(s=skip, q=quit): ").strip().lower()
        if ans == "q":
            break
        if ans == "s":
            continue
        client.send_message(f"/vkb_midi/{CHANNEL}/cc/{cc}", 64)
        time.sleep(0.15)
        client.send_message(f"/vkb_midi/{CHANNEL}/cc/{cc}", 72)
        time.sleep(0.15)
        client.send_message(f"/vkb_midi/{CHANNEL}/cc/{cc}", 64)
        print(f"    sent CC{cc} — the {knob} knob should have jumped to ~50%.")

    print("\nDone. Now in Serum's main menu: Save MIDI Map ->")
    print("  Serum 2 Presets/System/MIDI CC Maps/default.SerumMIDIMap  (overwrite)")
    print("Then tell the agent — it verifies the map file and the bindings by ear.")


if __name__ == "__main__":
    main()
