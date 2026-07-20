#!/usr/bin/env python
"""Decode Xfer's Serum 2 file container (.SerumMIDIMap, .SerumPreset, ...).

Container layout (verified against factory + saved files, 2026-07-17):

    "XferJson\\x00"            9-byte magic
    u32le manifest_len         length of the JSON manifest
    u32le 0
    JSON manifest              fileType, product, version, hash, ...
    u32le uncompressed_size    of the CBOR payload
    u32le 2                    payload format version
    zstd frame                 compresses a CBOR document

    manifest["hash"] == md5(zstd frame bytes)  -- integrity, not security.

Payloads seen:
  SerumMIDIMap: {"midiMap": [{"ccNum": N, "paramIDs": [id, ...]}, ...], ...}
  SerumPreset:  module tree (Filter, Env0.., Oscillator0.., Macro0..) with
                sparse name-keyed "plainParams" (only non-default values).

Usage:
  serumfile.py info <file>                        manifest + hash check
  serumfile.py map <file>                         list CC bindings of a MIDI map
  serumfile.py dump <file>                        full CBOR payload as JSON on stdout
  serumfile.py addcc <file> <cc> <paramID> <out>  add/replace one CC binding
  serumfile.py setparam <file> <Module> <kParam> <float> <out>
                                                  set one preset param value

Writing: re-encode CBOR -> zstd -> u32 sizes + md5(frame) into the manifest.
Round-trip is self-checked on every write (decode(encode(x)) == x).
"""

import hashlib
import json
import struct
import sys

import cbor2
import zstandard

MAGIC = b"XferJson\x00"


def read_container(path):
    data = open(path, "rb").read()
    if not data.startswith(MAGIC):
        raise ValueError(f"{path}: not an XferJson container")
    mlen, _zero = struct.unpack_from("<II", data, len(MAGIC))
    off = len(MAGIC) + 8
    manifest = json.loads(data[off:off + mlen])
    off += mlen
    usize, _ver = struct.unpack_from("<II", data, off)
    frame = data[off + 8:]
    payload = zstandard.ZstdDecompressor().decompress(frame, max_output_size=max(usize, 1) * 2)
    hash_ok = hashlib.md5(frame).hexdigest() == manifest.get("hash")
    return manifest, cbor2.loads(payload), hash_ok


def write_container(path, manifest, payload_obj):
    """Assemble a container; manifest['hash'] is (re)computed here."""
    cbor = cbor2.dumps(payload_obj)
    frame = zstandard.ZstdCompressor().compress(cbor)
    manifest = dict(manifest)
    manifest["hash"] = hashlib.md5(frame).hexdigest()
    mjson = json.dumps(manifest, separators=(",", ":")).encode()  # Serum writes compact JSON
    out = (MAGIC + struct.pack("<II", len(mjson), 0) + mjson
           + struct.pack("<II", len(cbor), 2) + frame)
    open(path, "wb").write(out)
    m2, p2, ok = read_container(path)          # self-check every write
    if not ok or p2 != payload_obj:
        raise RuntimeError(f"{path}: round-trip self-check FAILED")
    return len(out)


def main():
    argc = len(sys.argv)
    cmd = sys.argv[1] if argc > 1 else ""
    if not ((cmd in ("info", "map", "dump") and argc == 3)
            or (cmd == "addcc" and argc == 6)
            or (cmd == "setparam" and argc == 7)):
        print(__doc__)
        sys.exit(2)
    path = sys.argv[2]
    manifest, payload, hash_ok = read_container(path)

    if cmd == "info":
        print(json.dumps(manifest, indent=2))
        print(f"hash check: {'OK' if hash_ok else 'MISMATCH'}")
    elif cmd == "map":
        if not hash_ok:
            print("WARNING: hash mismatch", file=sys.stderr)
        for e in sorted(payload.get("midiMap", []), key=lambda x: x.get("ccNum", -1)):
            print(f"CC{e['ccNum']:>3} -> paramIDs {e['paramIDs']}")
    elif cmd == "dump":
        print(json.dumps(payload, indent=1, default=repr))
    elif cmd == "addcc":
        cc, pid, out = int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
        entries = [e for e in payload["midiMap"] if e.get("ccNum") != cc]
        entries.append({"ccNum": cc, "paramIDs": [pid]})
        payload["midiMap"] = sorted(entries, key=lambda e: e["ccNum"])
        n = write_container(out, manifest, payload)
        print(f"wrote {out} ({n} bytes): CC{cc} -> [{pid}], "
              f"{len(entries)} bindings, self-check OK")
    elif cmd == "setparam":
        module, kparam, value, out = (sys.argv[3], sys.argv[4],
                                      float(sys.argv[5]), sys.argv[6])
        mod = payload.get(module)
        if not isinstance(mod, dict):
            raise SystemExit(f"no module '{module}' in {path}")
        if not isinstance(mod.get("plainParams"), dict):
            mod["plainParams"] = {}      # sparse: 'default' means untouched
        old = mod["plainParams"].get(kparam, "(default)")
        mod["plainParams"][kparam] = value
        n = write_container(out, manifest, payload)
        print(f"wrote {out} ({n} bytes): {module}.{kparam} {old} -> {value}, "
              f"self-check OK")


if __name__ == "__main__":
    main()
