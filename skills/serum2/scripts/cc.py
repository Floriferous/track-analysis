#!/usr/bin/env python
"""Send MIDI CCs to Serum over the IAC bus — the reliable CC backbone.

Usage: cc.py <cc> <value> [<cc> <value> ...]     (values 0-127)

Rides the dedicated IAC port (default "IAC Driver Bus 2", override with
CLAUDE_CC_PORT) through Bitwig's Generic controller to the record-armed
track. This path is controller-independent; DrivenByMoss's vkb_midi CC
injection was observed to die silently (2026-07-20) and is not used for
CCs anymore. There is no readback — verify every send by capture.
"""

import os
import sys
import time

import mido


def main():
    args = sys.argv[1:]
    if not args or len(args) % 2:
        print(__doc__)
        sys.exit(2)
    pairs = [(int(args[i]), int(args[i + 1])) for i in range(0, len(args), 2)]
    port = mido.open_output(os.environ.get("CLAUDE_CC_PORT", "IAC Driver Bus 2"))
    for cc, value in pairs:
        port.send(mido.Message("control_change", channel=0, control=cc,
                               value=value))
        time.sleep(0.08)
        print(f"CC{cc} <- {value}")
    port.close()


if __name__ == "__main__":
    main()
