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

Importable: `capture(...)` returns hear.py's metrics dict, so a loop (see
converge.py) pays the numpy/scipy/soundfile import once instead of ~1.5 s of
interpreter startup per iteration.

Usage:
  python capture.py --project-dir <bitwig project dir> [--print-track-name PRINT]
                    [--slot 5] [--bars 2] [--scene N] [--solo N] [--fast] [--json]
"""
import argparse
import json as jsonlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import hear
from bw import BANK, bank_index, client, collect_feedback

QUANT = "/launcher/defaultQuantization"


class CaptureError(Exception):
    """An explainable refusal. `payload` is what --json prints — the
    "analysis failed"/"detail" shape predates this class and is parsed
    elsewhere, so it stays caller-controlled rather than derived."""

    def __init__(self, msg, payload=None):
        super().__init__(msg)
        self.payload = payload or {"error": msg}


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
            raise CaptureError(f"track {n} does not exist; tracks in the bank window: "
                               + ", ".join(f"{i}={v!r}" for i, v in seen.items()))
    else:
        hits = [i for i, v in seen.items() if v.strip().casefold() == name.strip().casefold()]
        if not hits:
            raise CaptureError(f"no track named {name!r} in the {BANK}-wide bank window "
                               f"(saw: {', '.join(repr(v) for v in seen.values())}) — "
                               "rename the print track, scroll the bank, or pass --print-track")
        if len(hits) > 1:
            raise CaptureError(f"{len(hits)} tracks named {name!r} (indices {hits}) — "
                               "pass --print-track to disambiguate")
        n = hits[0]
    if not state.get(f"/track/{n}/canHoldAudioData", (0,))[0]:
        raise CaptureError(f"track {n} ({seen[n]!r}) cannot hold audio data — it is not an "
                           "audio track, so recording there yields no WAV. Wrong --print-track?")
    return n


def capture(project_dir, print_track_name="PRINT", print_track=None, slot=5,
            bars=2.0, scene=None, solo=None, fast=False, width=False,
            pump=False, pump_band=None, report=False):
    """Record `bars` bars of whatever is playing and return hear.py's metrics.

    Raises CaptureError for every refusal, so a loop can decide whether to
    restore state and stop rather than being SystemExit'ed out mid-iteration."""
    if fast and pump:
        raise CaptureError("--fast and --pump are incompatible: the pump fold assumes the take "
                           "starts on a bar line, which is exactly what launch quantization "
                           "buys. Drop --fast for pump measurements.")

    rec_dir = Path(project_dir) / "recordings"
    c = client()

    # one cheap read: tempo -> bar length, so waits are exact rather than guessed
    # (the same dump resolves the print track and checks the capture slot)
    state = collect_feedback(1.5)
    if "/tempo/raw" not in state:
        raise CaptureError("no /tempo/raw in the feedback dump — without the tempo every "
                           "bar-length wait is a guess and the take is mistimed. "
                           "Check the OSC link (`bw.py ping`) and retry.")
    bpm = state["/tempo/raw"][0]
    if not 20 <= bpm <= 400:
        raise CaptureError(f"implausible tempo {bpm} from /tempo/raw — refusing to time a take on it")
    bar = 4 * 60.0 / bpm
    track = resolve_print_track(state, print_track, print_track_name)
    if scene is None and not state.get("/play", (0,))[0]:
        raise CaptureError("transport is not playing — the take would be silence. "
                           "Launch a scene first or pass --scene N.")

    prev_quant = state.get(QUANT, (None,))[0]
    if fast and prev_quant is None:
        raise CaptureError(f"cannot read {QUANT} — refusing to change launch quantization "
                           "without a value to restore")

    slot_key = f"/track/{track}/clip/{slot}/hasContent"
    if state.get(slot_key, (0,))[0]:
        # a full capture slot would PLAY on launch instead of recording
        c.send_message(f"/track/{track}/clip/{slot}/remove", 1)
        time.sleep(0.5)

    try:
        if fast:
            c.send_message(QUANT, "none")
            time.sleep(0.15)
        if solo is not None:
            c.send_message(f"/track/{solo}/solo", 1)
        if scene is not None:
            # only ever BEFORE arming: a scene fires every track's slot button and an
            # empty button is a STOP button, which would kill the print recording
            c.send_message(f"/scene/{scene}/launch", 1)
            time.sleep(0.35 if fast else bar + 0.3)  # unquantized starts are immediate

        before = newest_wav(rec_dir)
        c.send_message(f"/track/{track}/recarm", 1)
        time.sleep(0.2)
        c.send_message(f"/track/{track}/clip/{slot}/launch", 1)
        # quantized: one bar before recording starts, then the take itself.
        # The fast margin still covers the beat the analysis trims off the front
        # (start below) plus OSC latency, or the take is silently short.
        time.sleep(bars * bar + (bar / 4 + 0.25 if fast else bar + 0.2))
        # /track/N/stop is NOT an address (UnknownCommand, silently console-logged);
        # the per-track stop lives under clip/
        c.send_message(f"/track/{track}/clip/stop", 1)
        time.sleep(0.2 if fast else 0.4)  # quantized stops land on the next bar
        c.send_message(f"/track/{track}/recarm", 0)
    finally:
        if solo is not None:
            c.send_message(f"/track/{solo}/solo", 0)
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
        if fast:
            c.send_message(QUANT, prev_quant)

    wav = wait_for_new_wav(rec_dir, before)
    c.send_message(f"/track/{track}/clip/{slot}/remove", 1)  # keep the slot free; file persists
    if wav is None:
        raise CaptureError("no recording appeared — is the print track's input set to Master?")

    # start offset must be a whole number of beats: the pump fold assumes
    # t=0 sits on a beat, and recordings begin on a bar boundary
    try:
        return hear.analyze(str(wav), start=bar / 4, dur=bars * bar * 0.9, width=width,
                            pump_bpm=bpm if pump else None, pump_band=pump_band,
                            report=report)
    except hear.HearError as e:
        raise CaptureError(f"hear.py failed on {wav}: {e}",
                           {"error": "analysis failed", "detail": str(e)})


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

    t_start = time.monotonic()
    try:
        result = capture(args.project_dir, args.print_track_name, args.print_track,
                         args.slot, args.bars, args.scene, args.solo, args.fast,
                         args.width, args.pump, args.pump_band, report=not args.json)
    except CaptureError as e:
        if args.json:
            print(jsonlib.dumps(e.payload))  # stdout stays one parseable JSON line
            raise SystemExit(1)
        raise SystemExit(f"ERROR: {e}")
    if args.json:
        print(jsonlib.dumps(result))
    else:
        print(f"[capture loop: {time.monotonic() - t_start:.1f}s wall]")


if __name__ == "__main__":
    main()
