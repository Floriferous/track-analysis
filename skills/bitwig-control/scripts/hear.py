"""Quick timbre readout for a captured WAV — the fast half of the hearing loop.

Part of the bitwig-control skill: capture via Bitwig print-track recording
(see SKILL.md), then answer "what is this sound actually doing" in seconds —
fundamental, harmonics, band energy split, level. For beat-aware deep analysis
(grooves, pump, stems) use the track-analysis skill's pipeline instead.

Usage: python hear.py <audio.wav> [--start s] [--dur s]
"""
import argparse
import json

import numpy as np
import soundfile as sf

BANDS = {
    "sub (25-60Hz)": (25, 60),
    "bass (60-120Hz)": (60, 120),
    "low-mid (120-350Hz)": (120, 350),
    "mid (350-2k)": (350, 2000),
    "high-mid (2k-6k)": (2000, 6000),
    "high (6k-16k)": (6000, 16000),
}
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_name(hz):
    if hz <= 0:
        return "-"
    midi = 69 + 12 * np.log2(hz / 440.0)
    m = int(round(midi))
    cents = int(round((midi - m) * 100))
    return f"{NOTE_NAMES[m % 12]}{m // 12 - 1} {cents:+d}c"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("audio")
    ap.add_argument("--start", type=float, default=0.0, help="offset into the file (s)")
    ap.add_argument("--dur", type=float, default=None, help="analysis length (s)")
    ap.add_argument("--json", action="store_true", help="machine-readable output for loop scripts")
    args = ap.parse_args()

    y, sr = sf.read(args.audio, always_2d=True)
    y = y[int(args.start * sr):]
    if args.dur:
        y = y[:int(args.dur * sr)]
    if len(y) < sr // 2:
        msg = f"only {len(y) / sr:.2f}s of audio after --start/--dur; need >=0.5s"
        print(json.dumps({"error": msg}) if args.json else f"ERROR: {msg}")
        raise SystemExit(1)
    mono = y.mean(axis=1)
    dur = len(mono) / sr

    peak_db = 20 * np.log10(np.abs(y).max() + 1e-12)
    rms_db = 20 * np.log10(np.sqrt((mono ** 2).mean()) + 1e-12)
    result = {"file": args.audio, "dur_s": round(dur, 2), "sr": sr,
              "peak_dbfs": round(float(peak_db), 1), "rms_dbfs": round(float(rms_db), 1)}
    if not args.json:
        print(f"{args.audio}: {dur:.2f}s @ {sr}Hz | peak {peak_db:+.1f} dBFS, rms {rms_db:+.1f} dBFS")
    if peak_db < -60:
        if args.json:
            result["silence"] = True
            print(json.dumps(result))
        else:
            print("  (essentially silence — check routing/arming)")
        return

    # median magnitude spectrum: robust against transients, shows the sustained timbre
    # 16384 @ 44.1k -> 2.7 Hz bins: enough to tell E1 from F1 down in the sub
    n_fft = 16384
    hop = n_fft // 2
    frames = [mono[i:i + n_fft] * np.hanning(n_fft)
              for i in range(0, len(mono) - n_fft, hop)]
    S = np.median(np.abs(np.fft.rfft(np.array(frames), axis=1)), axis=0)
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)

    total = (S ** 2).sum() + 1e-12
    result["bands"] = {}
    if not args.json:
        print("band energy:")
    for name, (lo, hi) in BANDS.items():
        share = (S[(freqs >= lo) & (freqs < hi)] ** 2).sum() / total
        result["bands"][name.split(" ")[0]] = round(100 * float(share), 1)
        if not args.json:
            bar = "#" * int(round(share * 40))
            print(f"  {name:<20} {100 * share:5.1f}%  {bar}")

    # spectral peaks -> fundamental + harmonic series
    import scipy.signal
    peaks, props = scipy.signal.find_peaks(S, height=S.max() * 0.02, distance=int(10 * n_fft / sr))
    order = np.argsort(props["peak_heights"])[::-1][:10]
    top = sorted(peaks[order], key=lambda p: freqs[p])
    if len(top):
        f0 = freqs[top[0]]
        result["f0_hz"] = round(float(f0), 1)
        result["f0_note"] = note_name(f0)
        result["peaks"] = []
        if not args.json:
            print(f"lowest strong peak (fundamental): {f0:.1f} Hz = {note_name(f0)}")
            print("strongest peaks:")
        for p in sorted(top, key=lambda p: -S[p])[:8]:
            f = freqs[p]
            rel = 20 * np.log10(S[p] / S.max() + 1e-12)
            harm = f / f0
            tag = f"~H{harm:.0f}" if abs(harm - round(harm)) < 0.06 and harm >= 1 else ""
            result["peaks"].append({"hz": round(float(f), 1), "rel_db": round(float(rel), 1),
                                    "note": note_name(f), "harmonic": tag})
            if not args.json:
                print(f"  {f:7.1f} Hz  {rel:6.1f} dB  {note_name(f):<10} {tag}")
    if args.json:
        print(json.dumps(result))


if __name__ == "__main__":
    main()
