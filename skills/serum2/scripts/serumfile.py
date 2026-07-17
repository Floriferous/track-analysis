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
  serumfile.py info <file>      manifest + hash check
  serumfile.py map <file>       list CC bindings of a MIDI map
  serumfile.py dump <file>      full CBOR payload as JSON on stdout

Writing files back is untested territory: re-encode CBOR -> zstd -> update
uncompressed_size and manifest hash. Verify in Serum before trusting.
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


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("info", "map", "dump"):
        print(__doc__)
        sys.exit(2)
    cmd, path = sys.argv[1], sys.argv[2]
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


if __name__ == "__main__":
    main()
