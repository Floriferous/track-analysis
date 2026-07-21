"""Bitwig Studio control over OSC via the DrivenByMoss extension.

Part of the bitwig-control skill. Address reference: ../references/osc-protocol.md
Requires: DrivenByMoss's "Open Sound Control" controller active in Bitwig
(receive port 8000, send host 127.0.0.1, send port 9000 — the defaults).

Usage examples:
  python bw.py ping                       # verify the OSC link (listens for feedback)
  python bw.py state /device              # dump live state, filtered by address prefix
  python bw.py play | stop | tempo 125
  python bw.py note 1 36 100 --dur 0.2    # channel, note, velocity
  python bw.py clip-create 1 1 16         # track, slot, length in beats
  python bw.py clip-insert-file 1 1 /abs/path/groove.mid
  python bw.py clip-launch 1 1
  python bw.py params                     # names+values of the selected device page
  python bw.py param 3 0.5                # set knob 3 of the current page (0..1 float)
  python bw.py raw /device/+              # escape hatch: any address, typed args
"""
import argparse
import os
import re
import threading
import time

from pythonosc import dispatcher, osc_server, udp_client

HOST = os.environ.get("BITWIG_OSC_HOST", "127.0.0.1")
SEND_PORT = int(os.environ.get("BITWIG_OSC_SEND_PORT", "8000"))     # DBM listens here
FEEDBACK_PORT = int(os.environ.get("BITWIG_OSC_FEEDBACK_PORT", "9000"))  # DBM sends here
RESOLUTION = int(os.environ.get("BITWIG_OSC_RESOLUTION", "128"))    # DBM "Value resolution"
BANK = int(os.environ.get("BITWIG_OSC_BANK_SIZE", "8"))  # DBM "Bank page size"


def bank_index(n):
    """Track/slot/scene indices address a BANK-wide window; an index past it
    crashes the DrivenByMoss extension outright ('Index 8 out of bounds for
    length 8' — observed live). Refuse client-side."""
    n = int(n)
    if not 1 <= n <= BANK:
        raise SystemExit(f"index {n} outside the {BANK}-wide bank window "
                         f"(would CRASH the OSC extension); scroll the bank instead")
    return n


def client():
    return udp_client.SimpleUDPClient(HOST, SEND_PORT)


def typed(arg):
    for cast in (int, float):
        try:
            return cast(arg)
        except ValueError:
            pass
    return arg


# A COLD continuous write is silently swallowed: a numeric write to a
# RangedValue parameter only lands if that address was written recently.
# Priming (send a value, pause, send the target) makes it land. Discrete
# writes land cold and MUST NOT be primed — a primed /clip/launch fires
# twice, a primed /device/bypass toggles back, a primed /stop rewinds.
# So this is a strict ALLOWLIST of addresses that end in a value write, and
# it is anchored ($) because the /indicate, /reset and /touched children of
# those same parents are triggers.
_CONTINUOUS = re.compile(r"""^(
    /track/(\d+|selected)/(volume|pan)
  | /master/(volume|pan)
  | /track/\d+/send/\d+/volume
  | /track/param/\d+/value
  | /(device|primary|eq)/param/\d+/value
  | /device/lastparam/value
  | /device/(layer|drumpad)/(\d+|selected)/(volume|pan)
  | /device/(layer|drumpad)/(\d+|selected)/send/\d+/volume
  | /eq/(gain|freq|q)/\d+
  | /project/param/\d+/value
  | /click/volume | /crossfade | /preroll
)$""", re.X)


def is_continuous(address):
    """True if `address` is a value write that needs priming."""
    return bool(_CONTINUOUS.match(address))


def send(address, value=None, prime=True):
    """The one write path. Primes continuous addresses; sends everything
    else exactly once.

    Priming costs one extra packet and ~0.25s, and is the difference
    between a write landing and vanishing without a trace. Note DBM only
    accepts ONE argument per message (OSCParser passes a multi-arg Object[]
    straight into toInteger, which throws) — so value is a scalar."""
    c = client()
    if value is None:
        value = 1
    if prime and is_continuous(address):
        c.send_message(address, value)
        time.sleep(0.25)
    c.send_message(address, value)
    return value


def collect_feedback(seconds, send_refresh=True):
    """Listen on the feedback port; return {address: last args}.

    Feedback is change-driven and cache-deduplicated on the Bitwig side;
    /refresh forces a full cache-bypassing dump. Batches are framed by
    /update 1 ... /update 0, so after a dump has ended and the line has gone
    quiet we can stop early instead of sleeping out the full window."""
    state = {}
    last_msg = [time.monotonic()]
    saw_batch_end = [False]

    def handler(addr, *args):
        state[addr] = args
        last_msg[0] = time.monotonic()
        if addr == "/update" and args and args[0] == 0:
            saw_batch_end[0] = True

    disp = dispatcher.Dispatcher()
    disp.set_default_handler(handler)
    server = osc_server.ThreadingOSCUDPServer((HOST, FEEDBACK_PORT), disp)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    if send_refresh:
        client().send_message("/refresh", 1)
    start = time.monotonic()
    while time.monotonic() - start < seconds:
        if saw_batch_end[0] and time.monotonic() - last_msg[0] > 0.25:
            break
        time.sleep(0.05)
    server.shutdown()
    return state


def cmd_ping(_):
    state = collect_feedback(2.0)
    if state:
        print(f"OK: {len(state)} state addresses received from Bitwig")
        for k in ("/project/name", "/tempo/raw", "/track/selected/name", "/device/name"):
            if k in state:
                print(f"  {k} = {state[k]}")
    else:
        print("NO FEEDBACK. Checklist: Bitwig running? OSC controller added in "
              "Dashboard > Settings > Controllers (Utilities > Open Sound Control)? "
              f"Send host {HOST}, send port {FEEDBACK_PORT}, receive port {SEND_PORT}?")
        raise SystemExit(1)


def cmd_state(args):
    state = collect_feedback(2.0)
    prefix = args.prefix or "/"
    for addr in sorted(state):
        if addr.startswith(prefix):
            vals = " ".join(str(v) for v in state[addr])
            print(f"{addr} {vals}")


def cmd_params(_):
    state = collect_feedback(2.0)
    dev = state.get("/device/name", ("?",))[0]
    page = state.get("/device/page/selected/name", ("?",))[0]
    print(f"device: {dev} | page: {page}")
    for i in range(1, 9):
        name = state.get(f"/device/param/{i}/name", ("",))[0]
        val = state.get(f"/device/param/{i}/value", ("",))
        disp_val = state.get(f"/device/param/{i}/valueStr", val)
        if name:
            print(f"  {i}: {name} = {disp_val[0] if disp_val else '?'}")


def cmd_param(args):
    """Write, then verify via readback — the GUI user shares the cursor device,
    so a write can silently land on a different device than intended."""
    v = args.value
    value = round(v * (RESOLUTION - 1)) if isinstance(v, float) and 0 <= v <= 1 else int(v)
    key = f"/device/param/{args.index}/value"
    c = client()
    c.send_message(key, value)
    time.sleep(0.4)
    state = collect_feedback(1.2)
    got = state.get(key, (None,))[0]
    if got != value:
        # some states reject a cold absolute write (takeover-like); priming
        # with the current value first unlocks the move
        if got is not None:
            c.send_message(key, got)
            time.sleep(0.2)
        c.send_message(key, value)
        time.sleep(0.4)
        state = collect_feedback(1.2)
    got = state.get(key, (None,))[0]
    dev = state.get("/device/name", ("?",))[0]
    name = state.get(f"/device/param/{args.index}/name", ("?",))[0]
    vstr = state.get(f"/device/param/{args.index}/valueStr", ("",))[0]
    status = "OK" if got == value else f"MISMATCH: reads {got} — cursor moved? check `params`"
    print(f"{dev} / {name} <- {value}/{RESOLUTION - 1} ({vstr})  [{status}]")


def cmd_note(args):
    c = client()
    c.send_message(f"/vkb_midi/{args.channel}/note/{args.note}", args.velocity)
    time.sleep(args.dur)
    c.send_message(f"/vkb_midi/{args.channel}/note/{args.note}", 0)


def cmd_insert_file(args):
    """insertFile REPLACES the slot's content, and unnamed clips have blank
    names — hasContent is the only truthful emptiness check. Guard on it."""
    key = f"/track/{args.track}/clip/{args.slot}/hasContent"
    state = collect_feedback(1.5)
    has = state.get(key, (None,))[0]
    if has is None:
        print(f"cannot read {key} — slot outside the current bank window?")
        raise SystemExit(1)
    if has and not args.force:
        print(f"REFUSING: track {args.track} slot {args.slot} already has content "
              "(would be replaced). Pick an empty slot or pass --force.")
        raise SystemExit(1)
    client().send_message(f"/track/{args.track}/clip/{args.slot}/insertFile",
                          os.path.abspath(args.path))
    time.sleep(1.0)
    after = collect_feedback(1.5, send_refresh=True).get(key, (None,))[0]
    print(f"inserted; {key} = {after}")


def cmd_page(args):
    """Select a remote-control page. Digits address the current 8-wide
    *window* slot and +/- step one page — both silently no-op at the ends of
    the page list, so the only trustworthy form is BY NAME: rewind to the
    first page, then step forward reading /device/page/selected/name until
    it matches (the readback is the write)."""
    which = args.which
    c = client()

    def page_name():
        return collect_feedback(1.2).get("/device/page/selected/name", ("?",))[0]

    if which.isdigit() or which in ("+", "-"):
        addr = (f"/device/page/{which}/selected" if which.isdigit()
                else f"/device/param/{which}")
        c.send_message(addr, 1)
        time.sleep(0.4)
        print(f"page: {page_name()}")
        return
    target = which.lower()
    prev = None
    for _ in range(40):  # rewind to the first page (name stops changing)
        name = page_name()
        if name == prev:
            break
        prev = name
        c.send_message("/device/param/-", 1)
        time.sleep(0.35)
    seen = []
    for _ in range(40):
        name = page_name()
        if target in name.lower():
            print(f"page: {name}")
            return
        if seen and name == seen[-1]:
            break
        seen.append(name)
        c.send_message("/device/param/+", 1)
        time.sleep(0.35)
    print(f"NOT FOUND: no page matching '{which}' — saw: {', '.join(seen)}")
    raise SystemExit(1)


def cmd_pages(args):
    """Walk every remote-control page of the cursor device; dump the full
    param inventory as JSON. Page sets can be preset-dependent (Diva publishes
    params per active model) — enumerate per patch, not once per plugin."""
    import json
    c = client()
    c.send_message("/device/page/1/selected", 1)
    time.sleep(0.8)
    pages, seen = [], set()
    for _ in range(40):
        st = collect_feedback(1.5)
        name = st.get("/device/page/selected/name", ("?",))[0]
        if name in seen:
            break
        seen.add(name)
        params = [{"i": i,
                   "name": st.get(f"/device/param/{i}/name", ("",))[0],
                   "display": st.get(f"/device/param/{i}/valueStr", ("",))[0],
                   "value": st.get(f"/device/param/{i}/value", (None,))[0]}
                  for i in range(1, 9)
                  if st.get(f"/device/param/{i}/name", ("",))[0]]
        pages.append({"page": name, "device": st.get("/device/name", ("?",))[0], "params": params})
        c.send_message("/device/param/+", 1)
        time.sleep(0.6)
    print(json.dumps(pages, indent=1))


def cmd_lastparam(args):
    """Write the GUI-focused parameter (the user points, you turn). Cold
    writes can be rejected takeover-style, so always prime with the current
    value first; verify by readback like cmd_param."""
    v = args.value
    value = round(v * (RESOLUTION - 1)) if isinstance(v, float) and 0 <= v <= 1 else int(v)
    c = client()
    state = collect_feedback(1.2)
    cur = state.get("/device/lastparam/value", (None,))[0]
    name = state.get("/device/lastparam/name", ("?",))[0]
    if cur is None or not state.get("/device/lastparam/exists", (0,))[0]:
        print("no last-touched parameter — ask the user to wiggle the knob first")
        raise SystemExit(1)
    if args.expect and args.expect.lower() not in name.lower():
        print(f"REFUSING: focused param is '{name}', expected '{args.expect}' — "
              "the user's last click moved the focus; ask them to wiggle the target knob")
        raise SystemExit(1)
    c.send_message("/device/lastparam/value", cur)
    time.sleep(0.2)
    c.send_message("/device/lastparam/value", value)
    time.sleep(0.5)
    state = collect_feedback(1.2)
    got = state.get("/device/lastparam/value", (None,))[0]
    vstr = state.get("/device/lastparam/valueStr", ("",))[0]
    status = "OK" if got == value else f"MISMATCH: reads {got}"
    print(f"lastparam {name} <- {value}/{RESOLUTION - 1} ({vstr.strip()})  [{status}]")


def cmd_raw(args):
    vals = [typed(a) for a in args.args]
    if len(vals) > 1:
        # DBM hands a multi-arg Object[] straight to toInteger, which throws:
        # the message is dropped with only a console line. Refuse loudly.
        raise SystemExit(f"{args.address}: DrivenByMoss accepts one argument per "
                         f"message; got {len(vals)}")
    send(args.address, vals[0] if vals else None)
    primed = " (primed)" if is_continuous(args.address) else ""
    print(f"sent {args.address} {args.args}{primed}")


def simple(address, value=None):
    def run(args):
        val = value(args) if callable(value) else value
        send(address(args) if callable(address) else address, val)
    return run


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ping").set_defaults(fn=cmd_ping)
    p = sub.add_parser("state")
    p.add_argument("prefix", nargs="?", help="address prefix filter, e.g. /device")
    p.set_defaults(fn=cmd_state)

    sub.add_parser("play").set_defaults(fn=simple("/play"))
    sub.add_parser("stop").set_defaults(fn=simple("/stop"))
    sub.add_parser("record").set_defaults(fn=simple("/record"))
    p = sub.add_parser("tempo")
    p.add_argument("bpm", type=float)
    p.set_defaults(fn=simple("/tempo/raw", lambda a: a.bpm))

    p = sub.add_parser("note")
    p.add_argument("channel", type=int)
    p.add_argument("note", type=int)
    p.add_argument("velocity", type=int)
    p.add_argument("--dur", type=float, default=0.15)
    p.set_defaults(fn=cmd_note)

    for name, addr in (("clip-create", "create"), ("clip-launch", "launch")):
        p = sub.add_parser(name)
        p.add_argument("track", type=bank_index)
        p.add_argument("slot", type=bank_index)
        if name == "clip-create":
            p.add_argument("beats", type=int)
            p.set_defaults(fn=simple(lambda a: f"/track/{a.track}/clip/{a.slot}/create", lambda a: a.beats))
        else:
            p.set_defaults(fn=simple(lambda a: f"/track/{a.track}/clip/{a.slot}/launch"))
    p = sub.add_parser("clip-insert-file")
    p.add_argument("track", type=bank_index)
    p.add_argument("slot", type=bank_index)
    p.add_argument("path")
    p.add_argument("--force", action="store_true", help="overwrite a non-empty slot")
    p.set_defaults(fn=cmd_insert_file)
    sub.add_parser("undo").set_defaults(fn=simple("/undo"))
    sub.add_parser("redo").set_defaults(fn=simple("/redo"))

    sub.add_parser("params").set_defaults(fn=cmd_params)
    sub.add_parser("pages").set_defaults(fn=cmd_pages)
    p = sub.add_parser("lastparam")
    p.add_argument("value", type=typed, help="0..1 float (scaled) or raw int")
    p.add_argument("--expect", help="refuse unless the focused param's name contains this "
                                    "(the focus follows EVERY user click — verify before writing)")
    p.set_defaults(fn=cmd_lastparam)
    p = sub.add_parser("param")
    p.add_argument("index", type=int, choices=range(1, 9))
    p.add_argument("value", type=typed, help="0..1 float (scaled) or raw int")
    p.set_defaults(fn=cmd_param)
    p = sub.add_parser("page")
    p.add_argument("which", help="a page NAME (verified step-to; the reliable "
                   "form), or 1-8 (current window slot) or + or - (one step)")
    p.set_defaults(fn=cmd_page)
    p = sub.add_parser("device")
    p.add_argument("which", help="+ or - to walk the device chain")
    p.set_defaults(fn=simple(lambda a: f"/device/{a.which}"))

    for name, addr in (("browser-preset", "/browser/preset"),
                       ("browser-device-after", "/browser/device/after"),
                       ("browser-commit", "/browser/commit"),
                       ("browser-cancel", "/browser/cancel")):
        sub.add_parser(name).set_defaults(fn=simple(addr))
    p = sub.add_parser("browser-filter")
    p.add_argument("column", type=int, choices=range(1, 7))
    p.add_argument("dir", choices=["+", "-", "reset"])
    p.set_defaults(fn=simple(lambda a: f"/browser/filter/{a.column}/{a.dir}"))
    p = sub.add_parser("browser-result")
    p.add_argument("dir", choices=["+", "-"])
    p.set_defaults(fn=simple(lambda a: f"/browser/result/{a.dir}"))

    p = sub.add_parser("raw")
    p.add_argument("address")
    p.add_argument("args", nargs="*")
    p.set_defaults(fn=cmd_raw)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
