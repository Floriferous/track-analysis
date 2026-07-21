"""Drive one parameter until one measured metric hits a target — the tweak
loop with the human taken out of the middle.

  converge.py --project-dir <p> --param 3 --metric bands.high --target 1.4
  converge.py --project-dir <p> --track-volume 2 --metric width_side_pct.high --target 24

Bisects the knob over [--lo, --hi] (0..1 of its raw range), capturing after
every write, and stops when TWO CONSECUTIVE captures land inside --tol.

Everything below the bisection is scar tissue; none of it is optional:

- **Validity gate first.** Before looping it captures twice without touching
  anything (that spread IS the noise floor — patches drift on tens-of-seconds
  periods) and then drives the knob to both extremes to prove the metric
  actually follows it. A pump duck read off a bus with its own per-bar
  envelope measured 93% from the envelope, not the sidechain; that loop would
  have "converged" on a number that meant nothing.
- **Two consecutive in-tolerance captures.** Identical knob settings once
  scored 1.6 then 20.7 against one target. One match can be the drift's
  lucky phase.
- **Monotonicity is assumed but verified.** Several params here are not
  monotonic (zeroing Diva's FilterFM COLLAPSES the harmonic ladder instead
  of reducing it). A midpoint measuring outside its own bracket, or a bracket
  gone flat, stops the run instead of thrashing.
- **The cursor is shared.** The device is pinned and its name re-read every
  iteration; if it changed, the loop stops and does NOT blind-restore — the
  restore would land on whatever device the human just clicked.
- **The starting value is snapshotted and restored** on any failure. Undo is
  blind over OSC. Caveat measured here: the snapshot is the OSC *raw grid*
  position, and a knob the human set with the mouse can sit between grid
  points — restoring Compressor+ Make-up to its snapshotted raw 64 landed on
  +0.2 dB where it had read 0.0 dB (raw 63 is -0.2). Raise
  BITWIG_OSC_RESOLUTION if that residue matters, and never converge a knob
  whose exact current value is precious.
- **No scene launches mid-loop.** A scene fires every track's slot button and
  an empty slot button is a STOP button — it kills the print recording.
  --scene is honoured on the first capture only.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bw import BANK, RESOLUTION, bank_index, client, collect_feedback, send
from capture import CaptureError, capture

SETTLE = 0.35   # after a write, before the readback dump
DUMP = 1.2      # feedback listen window
# hear.py rounds every metric to one decimal, so two captures reading the same
# number are only "within 0.1", never noiseless. Sizing a tolerance off a
# measured spread of exactly 0 would make convergence unreachable by arithmetic.
QUANTIZATION = 0.05


class ConvergeError(Exception):
    """`restore=False` means the knob's address no longer means what it meant
    when we snapshotted it, so writing the old value back would corrupt
    whatever it points at now."""

    def __init__(self, msg, restore=True):
        super().__init__(msg)
        self.restore = restore


def dig(d, path):
    """Metric lookup by dotted path, with a usable error when it misses."""
    cur = d
    for depth, part in enumerate(path.split(".")):
        if not isinstance(cur, dict) or part not in cur:
            here = ".".join(path.split(".")[:depth]) or "<root>"
            keys = sorted(cur) if isinstance(cur, dict) else type(cur).__name__
            raise ConvergeError(f"metric path {path!r} missing at {part!r} (in {here}); "
                                f"available there: {keys}")
        cur = cur[part]
    if not isinstance(cur, (int, float)) or isinstance(cur, bool):
        raise ConvergeError(f"metric {path!r} is {cur!r}, not a number")
    return float(cur)


def prime_write(addr, raw, state):
    """One absolute write, primed with the value the address CURRENTLY reads.

    Not bw.send(): that primes by sending the target twice, which is enough to
    warm a cold address but not to get past the takeover-style rejection a
    device param can apply — measured here, four packets of 51 left
    /device/param/8/value sitting at 64. Priming with the current value is what
    bw.py's cmd_param has always done, and it is the path with the clean
    record. `state` is a dump the caller already paid for."""
    cur = state.get(addr, (None,))[0]
    c = client()
    c.send_message(addr, raw if cur is None else cur)
    time.sleep(0.25)
    c.send_message(addr, raw)
    time.sleep(SETTLE)


class Knob:
    """A raw-int control with a readback address. Bisection works in 0..1;
    the raw grid is what Bitwig actually stores, and two 0..1 values that
    round to the same raw int are the same knob position."""

    def __init__(self, addr, raw_max, label, identity_addr, identity):
        self.addr, self.raw_max, self.label = addr, raw_max, label
        self.identity_addr, self.identity = identity_addr, identity

    def raw(self, x):
        return max(0, min(self.raw_max, int(round(x * self.raw_max))))

    def write(self, x):
        """Write and verify — the readback IS the write. Every pass re-checks
        that the address still points at the thing we snapshotted, because the
        GUI user moves the cursor between our write and our read."""
        raw = self.raw(x)
        got = None
        for _ in range(3):  # read, write, read, write, read
            st = collect_feedback(DUMP)
            now = st.get(self.identity_addr, ("?",))[0]
            if now != self.identity:
                raise ConvergeError(
                    f"{self.identity_addr} changed {self.identity!r} -> {now!r} mid-run: the "
                    f"cursor moved, so {self.addr} no longer addresses what we snapshotted.",
                    restore=False)
            got = st.get(self.addr, (None,))[0]
            if got == raw:
                return raw
            if got is None:
                raise ConvergeError(f"{self.addr} is not in the feedback dump — outside the "
                                    "bank window, or the device lost its page?")
            prime_write(self.addr, raw, st)
        raise ConvergeError(f"{self.addr} <- {raw} did not read back after 2 tries (reads {got})")


def build_knob(state, args):
    if args.param is not None:
        dev = state.get("/device/name", ("",))[0]
        if not state.get("/device/exists", (0,))[0] or not dev:
            raise ConvergeError("no cursor device — click the device you want tuned, "
                                "or walk to it with `bw.py device +`")
        name = state.get(f"/device/param/{args.param}/name", ("",))[0]
        if not name:
            raise ConvergeError(f"param {args.param} is empty on page "
                                f"{state.get('/device/page/selected/name', ('?',))[0]!r} of {dev} — "
                                "run `bw.py params` and pick a listed index")
        if args.device and args.device.lower() not in dev.lower():
            raise ConvergeError(f"cursor device is {dev!r}, expected {args.device!r}")
        return Knob(f"/device/param/{args.param}/value", RESOLUTION - 1,
                    f"{dev} / {name} (param {args.param})", "/device/name", dev)
    n = args.track_volume
    if not state.get(f"/track/{n}/exists", (0,))[0]:
        raise ConvergeError(f"track {n} does not exist in the {BANK}-wide bank window")
    tname = state.get(f"/track/{n}/name", ("",))[0]
    # 128 track-volume steps are ~0.3 dB apart near unity — plenty of grid for a bisect
    return Knob(f"/track/{n}/volume", 127, f"track {n} {tname!r} volume",
                f"/track/{n}/name", tname)


def _log(line):
    # unbuffered: a run is minutes long and its transcript is the point, so it
    # must interleave correctly with the stderr failure path when piped
    print(line, flush=True)


def search(knob, measure, metric, target, tol, lo, hi, max_iter, noise_captures, log=_log):
    """Gate the metric, then bisect the knob. Returns (x, raw, m, m2, tol) once
    two consecutive captures land inside tol; raises ConvergeError otherwise.

    `knob` is anything with .write(x)->raw, .raw(x)->int and .raw_max, and
    `measure` is a zero-arg call returning the metric — which is what makes the
    refusal branches (non-monotonic, flat, exhausted) testable without a DAW."""
    # --- validity gate: noise floor first, then "does the metric follow the knob at all"
    base = [measure() for _ in range(noise_captures)]
    noise = max(max(base) - min(base), QUANTIZATION)
    log(f"noise:  {noise_captures} captures untouched -> "
        f"{', '.join(f'{v:g}' for v in base)}  (floor {noise:g})")
    if tol is not None and tol < noise:
        raise ConvergeError(f"--tol {tol:g} is tighter than the measured noise floor "
                            f"{noise:g}: two consecutive captures inside it would be luck, "
                            f"not convergence. Use --tol {2 * noise:g} or more.")
    auto = tol is None
    tol = 2 * noise if auto else tol
    log(f"tol:    {tol:g}" + (" (auto = 2x noise floor)" if auto else ""))

    a, b = lo, hi
    knob.write(a); ma = measure()
    knob.write(b); mb = measure()
    span = abs(mb - ma)
    log(f"gate:   {metric} {ma:g} at {a:.3f} -> {mb:g} at {b:.3f}  (span {span:g})")
    if span <= 2 * noise:
        raise ConvergeError(
            f"{metric} moves {span:g} across the whole search range but the noise floor is "
            f"{noise:g} — this knob does not control this metric (or not here). Refusing to "
            "converge on noise; pick another param, another metric, or isolate the source "
            "(--solo / --pump-band).")
    if span < 4 * noise:
        # passing the gate is a floor, not a proof: at span ~2x noise the first
        # midpoint usually "converges" simply because every setting reads the
        # same. Measured: Hats level vs width_side_pct.high, span 0.8 / noise
        # 0.2, converged on iteration 1 at a knob position that means nothing.
        log(f"WEAK:   span {span:g} is only {span / noise:.1f}x the noise floor — this knob "
            f"barely moves {metric}. Treat the result as an upper bound on the effect, not "
            "as a tuned value.")
    direction = 1.0 if mb > ma else -1.0
    if not min(ma, mb) - tol <= target <= max(ma, mb) + tol:
        raise ConvergeError(f"target {target:g} is outside the reachable range "
                            f"[{min(ma, mb):g}, {max(ma, mb):g}] over {a:.3f}..{b:.3f} — widen "
                            "--lo/--hi, or the target is wrong for this control")

    # --- bisect; the bracket always straddles the target
    for i in range(1, max_iter + 1):
        x = (a + b) / 2
        raw = knob.write(x)
        m = measure()
        err = m - target
        log(f"iter {i:2d}  {x:.4f} (raw {raw:3d})  {metric} = {m:<8g} "
            f"err {err:+.3g}  bracket [{a:.4f},{b:.4f}]")

        # a midpoint outside its own bracket's readings is the non-monotonic
        # signature (FilterFM: zeroing it COLLAPSED the ladder rather than
        # reducing it). 2x noise so drift alone does not trip it.
        if not min(ma, mb) - 2 * noise <= m <= max(ma, mb) + 2 * noise:
            raise ConvergeError(
                f"NON-MONOTONIC: midpoint {x:.4f} reads {m:g}, outside the bracket's own "
                f"readings [{min(ma, mb):g}, {max(ma, mb):g}] +/- {2 * noise:g}. Bisection "
                "assumes the metric is monotonic in the param; it is not here. Sweep the "
                "range by hand and look at the shape.")

        if abs(err) <= tol:
            m2 = measure()
            ok = abs(m2 - target) <= tol
            log(f"        confirm at {x:.4f}: {m2:g} "
                f"({'in tolerance' if ok else 'DRIFTED OUT — one match was luck'})")
            if ok:
                return x, raw, m, m2, tol
            m, err = m2, m2 - target  # the confirming capture is the honest reading

        if err * direction > 0:
            b, mb = x, m
        else:
            a, ma = x, m
        if abs(ma - mb) <= noise:
            raise ConvergeError(
                f"FLAT: the bracket [{a:.4f},{b:.4f}] spans {abs(ma - mb):g} of {metric}, at "
                f"or under the noise floor {noise:g}, and the target {target:g} is not inside "
                "it. The metric has stopped responding here — not reachable by this knob.")
        if abs(knob.raw(b) - knob.raw(a)) <= 1:
            raise ConvergeError(
                f"EXHAUSTED: bracket collapsed to adjacent raw steps ({knob.raw(a)}, "
                f"{knob.raw(b)}) reading {ma:g}/{mb:g}; target {target:g} falls between two "
                "settings the knob cannot express. Raise BITWIG_OSC_RESOLUTION or loosen --tol.")
    raise ConvergeError(f"did not converge in {max_iter} iterations; last bracket "
                        f"[{a:.4f},{b:.4f}] -> {ma:g}..{mb:g}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project-dir", required=True)
    tgt = ap.add_mutually_exclusive_group(required=True)
    tgt.add_argument("--param", type=int, choices=range(1, 9),
                     help="cursor-device remote-control knob (run `bw.py params` first)")
    tgt.add_argument("--track-volume", type=bank_index, help="a track fader instead of a device knob")
    ap.add_argument("--metric", required=True,
                    help="dotted path into hear.py's dict: bands.high, "
                         "width_side_pct.high, pump_duck_pct, f0_hz, rms_dbfs")
    ap.add_argument("--target", type=float, required=True)
    ap.add_argument("--tol", type=float, default=None,
                    help="default: 2x the measured capture-to-capture noise floor")
    ap.add_argument("--lo", type=float, default=0.0, help="search range low end (0..1)")
    ap.add_argument("--hi", type=float, default=1.0)
    ap.add_argument("--max-iter", type=int, default=12, help="cap on captures inside the loop")
    ap.add_argument("--device", help="refuse unless the cursor device's name contains this")
    ap.add_argument("--noise-captures", type=int, default=2,
                    help="captures at the untouched starting value to size the noise floor")
    # passthrough to capture()
    ap.add_argument("--bars", type=float, default=2)
    ap.add_argument("--slot", type=bank_index, default=5)
    ap.add_argument("--print-track-name", default="PRINT")
    ap.add_argument("--print-track", type=bank_index, default=None)
    ap.add_argument("--solo", type=bank_index)
    ap.add_argument("--scene", type=bank_index,
                    help="launch once, before the FIRST capture only (a mid-loop scene "
                         "launch stops the print recording)")
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--width", action="store_true")
    ap.add_argument("--pump", action="store_true")
    ap.add_argument("--pump-band", default=None, metavar="LO,HI")
    args = ap.parse_args()

    if not 0.0 <= args.lo < args.hi <= 1.0:
        raise SystemExit(f"need 0 <= --lo < --hi <= 1, got {args.lo}..{args.hi}")
    if args.noise_captures < 2:
        raise SystemExit("--noise-captures must be >= 2: one capture measures no spread")
    # the metric decides which analyses have to run; asking for width_side_pct
    # without --width just yields a missing-key error six seconds later
    if args.metric.startswith("width_side_pct"):
        args.width = True
    if args.metric.startswith("pump_"):
        args.pump = True

    t0 = time.monotonic()
    n_caps = [0]
    scene = [args.scene]

    def measure():
        """One capture -> the scalar under --metric. Consumes --scene once."""
        m = capture(args.project_dir, print_track_name=args.print_track_name,
                    print_track=args.print_track, slot=args.slot, bars=args.bars,
                    scene=scene[0], solo=args.solo, fast=args.fast, width=args.width,
                    pump=args.pump, pump_band=args.pump_band)
        scene[0] = None  # never again: a scene launch mid-loop stops the recording
        n_caps[0] += 1
        if m.get("silence"):
            raise ConvergeError("capture was silence (peak < -60 dBFS) — nothing is playing, "
                                "or the solo/mute state killed the source")
        return dig(m, args.metric)

    state = collect_feedback(DUMP)
    knob = build_knob(state, args)
    start_raw = state.get(knob.addr, (None,))[0]
    if not isinstance(start_raw, int):
        raise SystemExit(f"cannot read {knob.addr} (got {start_raw!r}) — refusing to move a "
                         "control whose starting value we could not snapshot")
    was_pinned = state.get("/device/pinned", (0,))[0]
    if args.param is not None and not was_pinned:
        send("/device/pinned", 1)  # the GUI user shares the cursor device
        time.sleep(0.3)

    print(f"target: {args.metric} = {args.target} on {knob.label}", flush=True)
    print(f"knob:   raw {start_raw}/{knob.raw_max} at start, searching "
          f"{args.lo:.3f}..{args.hi:.3f}", flush=True)

    converged = None
    try:
        converged = search(knob, measure, args.metric, args.target, args.tol,
                           args.lo, args.hi, args.max_iter, args.noise_captures)
        x, raw, m, m2, tol = converged
        print(f"\nCONVERGED  {args.metric} = {m:g}, {m2:g} (target {args.target:g} +/- {tol:g})",
              flush=True)
        print(f"  {knob.label} left at raw {raw}/{knob.raw_max} ({x:.4f}); was {start_raw}",
              flush=True)
    except (ConvergeError, CaptureError, KeyboardInterrupt) as e:
        kind = "INTERRUPTED" if isinstance(e, KeyboardInterrupt) else "STOPPED"
        print(f"\n{kind}: {e}", file=sys.stderr, flush=True)
        if getattr(e, "restore", True):
            try:
                prime_write(knob.addr, start_raw, collect_feedback(DUMP))
                got = collect_feedback(DUMP).get(knob.addr, (None,))[0]
                print(f"restored {knob.addr} -> {start_raw} (reads {got})", file=sys.stderr)
            except Exception as re:  # noqa: BLE001 - best-effort; report either outcome
                print(f"RESTORE FAILED ({re}) — {knob.label} is at an unknown value; "
                      f"it started at raw {start_raw}", file=sys.stderr)
        else:
            print(f"NOT restored (the address moved) — {knob.label} started at raw "
                  f"{start_raw}; set it by hand", file=sys.stderr)
    finally:
        if args.param is not None and not was_pinned:
            send("/device/pinned", 0)  # leave the human's cursor as we found it

    print(f"{n_caps[0]} captures, {time.monotonic() - t0:.0f}s wall", flush=True)
    raise SystemExit(0 if converged else 1)


if __name__ == "__main__":
    main()
