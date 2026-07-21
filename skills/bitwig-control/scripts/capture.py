"""One-shot capture-and-measure: the fast half of the tweak loop.

Records N bars of the master bus into a print-track clip slot, waits for the
WAV to land in the project's recordings/ folder, analyzes it (hear.py), and
cleans the slot up — leaving whatever is playing still playing, so the next
iteration only pays for the recording itself.

The print track is found BY NAME (default "PRINT"): track indices shift the
moment anyone inserts a track above it, and recording onto an instrument track
produces no WAV and a misleading error. --print-track overrides.

Assumes the print track's input is the Master bus (SKILL.md setup) and that
something is already playing (launch a scene first, or pass --scene).

Usage:
  python capture.py --project-dir <bitwig project dir> [--print-track-name PRINT]
                    [--slot 5] [--bars 2] [--scene N] [--solo N] [--fast] [--json]
"""
import argparse
import json as jsonlib
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bw import BANK, bank_index, client, collect_feedback

QUANT = "/launcher/defaultQuantization"


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


def resolve_print_track(state, override, name):
    """Index of the print track, verified to exist and to hold audio.

    An index is only a snapshot of the current track order; the name is the
    thing the user actually means. Either way we check canHoldAudioData —
    arming an instrument track records nothing and blames the Master input."""
    seen = {i: state.get(f"/track/{i}/name", ("",))[0] for i in range(1, BANK + 1)
            if state.get(f"/track/{i}/exists", (0,))[0]}
    if override is not None:
        n = override
        if n not in seen:
            raise SystemExit(f"track {n} does not exist; tracks in the bank window: "
                             + ", ".join(f"{i}={v!r}" for i, v in seen.items()))
    else:
        hits = [i for i, v in seen.items() if v.strip().casefold() == name.strip().casefold()]
        if not hits:
            raise SystemExit(f"no track named {name!r} in the {BANK}-wide bank window "
                             f"(saw: {', '.join(repr(v) for v in seen.values())}) — "
                             "rename the print track, scroll the bank, or pass --print-track")
        if len(hits) > 1:
            raise SystemExit(f"{len(hits)} tracks named {name!r} (indices {hits}) — "
                             "pass --print-track to disambiguate")
        n = hits[0]
    if not state.get(f"/track/{n}/canHoldAudioData", (0,))[0]:
        raise SystemExit(f"track {n} ({seen[n]!r}) cannot hold audio data — it is not an "
                         "audio track, so recording there yields no WAV. Wrong --print-track?")
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-dir", required=True, help="Bitwig project folder (holds recordings/)")
    ap.add_argument("--print-track-name", default="PRINT", help="resolve the print track by name")
    ap.add_argument("--print-track", type=bank_index, default=None,
                    help="override the name lookup with an explicit track index")
    ap.add_argument("--slot", type=bank_index, default=5, help="capture slot on the print track (an unused row)")
    ap.add_argument("--bars", type=float, default=2)
    ap.add_argument("--scene", type=bank_index, help="launch this scene first (else records what's playing)")
    ap.add_argument("--solo", type=bank_index, help="solo this track during the capture")
    ap.add_argument("--fast", action="store_true",
                    help="turn launch quantization off for the capture (saves a bar per "
                         "launch, restored afterwards). The take no longer starts on a "
                         "bar line, so it is not usable with --pump")
    ap.add_argument("--json", action="store_true", help="machine-readable hear.py output")
    ap.add_argument("--width", action="store_true", help="per-band stereo side share")
    ap.add_argument("--pump", action="store_true", help="measure duck depth/shape at the project tempo")
    ap.add_argument("--pump-band", default=None, metavar="LO,HI", help="band-limit the pump envelope (Hz)")
    args = ap.parse_args()

    if args.fast and args.pump:
        raise SystemExit("--fast and --pump are incompatible: the pump fold assumes the take "
                         "starts on a bar line, which is exactly what launch quantization "
                         "buys. Drop --fast for pump measurements.")

    t_start = time.monotonic()
    rec_dir = Path(args.project_dir) / "recordings"
    c = client()

    # one cheap read: tempo -> bar length, so waits are exact rather than guessed
    # (the same dump resolves the print track and checks the capture slot)
    state = collect_feedback(1.5)
    if "/tempo/raw" not in state:
        raise SystemExit("no /tempo/raw in the feedback dump — without the tempo every "
                         "bar-length wait is a guess and the take is mistimed. "
                         "Check the OSC link (`bw.py ping`) and retry.")
    bpm = state["/tempo/raw"][0]
    if not 20 <= bpm <= 400:
        raise SystemExit(f"implausible tempo {bpm} from /tempo/raw — refusing to time a take on it")
    bar = 4 * 60.0 / bpm
    track = resolve_print_track(state, args.print_track, args.print_track_name)
    if args.scene is None and not state.get("/play", (0,))[0]:
        raise SystemExit("transport is not playing — the take would be silence. "
                         "Launch a scene first or pass --scene N.")

    prev_quant = state.get(QUANT, (None,))[0]
    if args.fast and prev_quant is None:
        raise SystemExit(f"cannot read {QUANT} — refusing to change launch quantization "
                         "without a value to restore")

    slot_key = f"/track/{track}/clip/{args.slot}/hasContent"
    if state.get(slot_key, (0,))[0]:
        # a full capture slot would PLAY on launch instead of recording
        c.send_message(f"/track/{track}/clip/{args.slot}/remove", 1)
        time.sleep(0.5)

    try:
        if args.fast:
            c.send_message(QUANT, "none")
            time.sleep(0.15)
        if args.solo is not None:
            c.send_message(f"/track/{args.solo}/solo", 1)
        if args.scene is not None:
            # only ever BEFORE arming: a scene fires every track's slot button and an
            # empty button is a STOP button, which would kill the print recording
            c.send_message(f"/scene/{args.scene}/launch", 1)
            time.sleep(0.35 if args.fast else bar + 0.3)  # unquantized starts are immediate

        before = newest_wav(rec_dir)
        c.send_message(f"/track/{track}/recarm", 1)
        time.sleep(0.2)
        c.send_message(f"/track/{track}/clip/{args.slot}/launch", 1)
        # quantized: one bar before recording starts, then the take itself.
        # The fast margin still covers the beat the analysis trims off the front
        # (--start below) plus OSC latency, or the take is silently short.
        time.sleep(args.bars * bar + (bar / 4 + 0.25 if args.fast else bar + 0.2))
        # /track/N/stop is NOT an address (UnknownCommand, silently console-logged);
        # the per-track stop lives under clip/
        c.send_message(f"/track/{track}/clip/stop", 1)
        time.sleep(0.2 if args.fast else 0.4)  # quantized stops land on the next bar
        c.send_message(f"/track/{track}/recarm", 0)
    finally:
        if args.solo is not None:
            c.send_message(f"/track/{args.solo}/solo", 0)
            # Clearing solo does NOT reliably clear the mutes it implied: a soloed
            # capture was observed leaving two unrelated tracks muted, which then
            # silently poisons every later measurement (the mix reads as if those
            # parts do not exist). Restore whatever was muted before we started.
            time.sleep(0.4)
            after = collect_feedback(1.2)
            for i in range(1, BANK + 1):
                was = state.get(f"/track/{i}/mute", (0,))[0]
                now = after.get(f"/track/{i}/mute", (0,))[0]
                if now != was:
                    c.send_message(f"/track/{i}/mute", int(was))
                    print(f"restored mute={int(was)} on track {i}", file=sys.stderr)
        if args.fast:
            c.send_message(QUANT, prev_quant)

    wav = wait_for_new_wav(rec_dir, before)
    c.send_message(f"/track/{track}/clip/{args.slot}/remove", 1)  # keep the slot free; file persists
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
    if args.width:
        cmd += ["--width"]
    if args.pump:
        cmd += ["--pump-bpm", str(bpm)]
    if args.pump_band:
        cmd += ["--pump-band", args.pump_band]
    r = subprocess.run(cmd, capture_output=True, text=True)
    out, err = r.stdout.strip(), r.stderr.strip()
    if r.returncode != 0 or not out:
        # hear.py reports expected failures on stdout and crashes on stderr;
        # discarding stderr leaves the caller staring at a blank line
        detail = err or out or f"hear.py exited {r.returncode} with no output"
        if args.json:
            print(out if out.startswith("{") else
                  jsonlib.dumps({"error": "analysis failed", "detail": detail.splitlines()[-1]}))
        else:
            print(f"ERROR: hear.py failed on {wav}:\n{detail}")
        raise SystemExit(1)
    print(out)
    if err:
        print(err, file=sys.stderr)  # stdout stays a single JSON line
    if not args.json:
        print(f"[capture loop: {time.monotonic() - t_start:.1f}s wall]")


if __name__ == "__main__":
    main()
