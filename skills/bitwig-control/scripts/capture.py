"""One-shot capture-and-measure: the fast half of the tweak loop.

Records N bars of the master bus into a print-track clip slot, waits for the
WAV to land in the project's recordings/ folder, analyzes it (hear.py), and
cleans the slot up — leaving whatever is playing still playing, so the next
iteration only pays for the recording itself.

Assumes the print track's input is the Master bus (SKILL.md setup) and that
something is already playing (launch a scene first, or pass --scene).

Usage:
  python capture.py --project-dir <bitwig project dir> [--print-track 1]
                    [--slot 5] [--bars 2] [--scene N] [--solo N] [--json]
"""
import argparse
import json as jsonlib
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bw import client, collect_feedback


def newest_wav(rec_dir):
    wavs = list(rec_dir.glob("*.wav"))
    return max(wavs, key=lambda p: p.stat().st_mtime) if wavs else None


def wait_for_new_wav(rec_dir, before, timeout=10):
    """Poll for a new, size-stable wav after recording stops."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        w = newest_wav(rec_dir)
        if w and w != before:
            s1 = w.stat().st_size
            time.sleep(0.3)
            if w.stat().st_size == s1 and s1 > 100_000:
                return w
        time.sleep(0.2)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-dir", required=True, help="Bitwig project folder (holds recordings/)")
    ap.add_argument("--print-track", type=int, default=1)
    ap.add_argument("--slot", type=int, default=5, help="capture slot on the print track (an unused row)")
    ap.add_argument("--bars", type=float, default=2)
    ap.add_argument("--scene", type=int, help="launch this scene first (else records what's playing)")
    ap.add_argument("--solo", type=int, help="solo this track during the capture")
    ap.add_argument("--json", action="store_true", help="machine-readable hear.py output")
    ap.add_argument("--pump", action="store_true", help="measure duck depth/shape at the project tempo")
    ap.add_argument("--pump-band", default=None, metavar="LO,HI", help="band-limit the pump envelope (Hz)")
    args = ap.parse_args()

    t_start = time.monotonic()
    rec_dir = Path(args.project_dir) / "recordings"
    c = client()

    # one cheap read: tempo -> bar length, so waits are exact rather than guessed
    # (same dump also tells us if the capture slot is stale)
    state = collect_feedback(1.5)
    bpm = state.get("/tempo/raw", (120.0,))[0]
    bar = 4 * 60.0 / bpm
    slot_key = f"/track/{args.print_track}/clip/{args.slot}/hasContent"
    if state.get(slot_key, (0,))[0]:
        # a full capture slot would PLAY on launch instead of recording
        c.send_message(f"/track/{args.print_track}/clip/{args.slot}/remove", 1)
        time.sleep(0.5)

    if args.solo is not None:
        c.send_message(f"/track/{args.solo}/solo", 1)
    if args.scene is not None:
        c.send_message(f"/scene/{args.scene}/launch", 1)
        time.sleep(bar + 0.3)  # launch quantization: wait one bar for it to actually start

    before = newest_wav(rec_dir)
    c.send_message(f"/track/{args.print_track}/recarm", 1)
    time.sleep(0.2)
    c.send_message(f"/track/{args.print_track}/clip/{args.slot}/launch", 1)
    # record start is bar-quantized, then the take itself
    time.sleep(bar + args.bars * bar + 0.2)
    c.send_message(f"/track/{args.print_track}/stop", 1)
    time.sleep(0.4)
    c.send_message(f"/track/{args.print_track}/recarm", 0)
    if args.solo is not None:
        c.send_message(f"/track/{args.solo}/solo", 0)

    wav = wait_for_new_wav(rec_dir, before)
    c.send_message(f"/track/{args.print_track}/clip/{args.slot}/remove", 1)  # keep the slot free; file persists
    if wav is None:
        print(jsonlib.dumps({"error": "no recording appeared"}) if args.json
              else "ERROR: no recording appeared — is the print track's input set to Master?")
        raise SystemExit(1)

    hear = Path(__file__).parent / "hear.py"
    # start offset must be a whole number of beats: the pump fold assumes
    # t=0 sits on a beat, and recordings begin on a bar boundary
    cmd = [sys.executable, str(hear), str(wav), "--start", str(bar / 4), "--dur", str(args.bars * bar * 0.9)]
    if args.json:
        cmd.append("--json")
    if args.pump:
        cmd += ["--pump-bpm", str(bpm)]
    if args.pump_band:
        cmd += ["--pump-band", args.pump_band]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    print(out.rstrip())
    if not args.json:
        print(f"[capture loop: {time.monotonic() - t_start:.1f}s wall]")


if __name__ == "__main__":
    main()
