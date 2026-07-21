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
    ap.add_argument("--pump-bpm", type=float, default=None,
                    help="fold the level envelope onto one beat at this BPM: "
                         "reports duck depth %% and minimum position (sidechain tuning)")
    ap.add_argument("--width", action="store_true",
                    help="per-band stereo side share (%%): 0 = mono, ~25 = a wide "
                         "techno hat. Needs a stereo file.")
    ap.add_argument("--pump-band", default=None, metavar="LO,HI",
                    help="band-limit the pump envelope (Hz), e.g. 120,300 to watch "
                         "bass harmonics while a kick occupies the sub")
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

    def spectrum(sig):
        frames = [sig[i:i + n_fft] * np.hanning(n_fft)
                  for i in range(0, len(sig) - n_fft, hop)]
        return np.median(np.abs(np.fft.rfft(np.array(frames), axis=1)), axis=0)

    S = spectrum(mono)
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

    # Stereo width. Mono sources read ~0; a dead-centre element is the usual
    # reason a part sounds small next to a reference that measures ~25% side.
    if args.width:
        if y.shape[1] < 2:
            if not args.json:
                print("stereo width: (mono file)")
        else:
            # mean power, NOT the median spectrum used for timbre above: width is
            # about how energy is distributed, and a median across frames
            # underweights transients — which is most of what a hat *is*.
            def power(sig):
                frames = [sig[i:i + n_fft] * np.hanning(n_fft)
                          for i in range(0, len(sig) - n_fft, hop)]
                return (np.abs(np.fft.rfft(np.array(frames), axis=1)) ** 2).mean(axis=0)

            Sm, Ss = power(y.mean(axis=1)), power((y[:, 0] - y[:, 1]) / 2)
            result["width_side_pct"] = {}
            if not args.json:
                print("stereo width (side share):")
            for name, (lo, hi) in BANDS.items():
                sel = (freqs >= lo) & (freqs < hi)
                me, se = Sm[sel].sum(), Ss[sel].sum()
                pct = 100 * float(se / (me + se + 1e-20))
                result["width_side_pct"][name.split(" ")[0]] = round(pct, 1)
                if not args.json:
                    print(f"  {name:<20} {pct:5.1f}%  {'#' * int(round(pct * 0.4))}")

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
    if args.pump_bpm:
        if args.pump_band:
            import scipy.signal as ss
            lo, hi = (float(x) for x in args.pump_band.split(","))
            sos = ss.butter(4, [lo, hi], btype="band", fs=sr, output="sos")
            mono = ss.sosfilt(sos, mono)
        # 30ms RMS envelope folded onto one beat -> pump curve
        win = int(sr * 0.030)
        hop_e = int(sr * 0.004)  # hop must be finer than the fold bins or bins alias empty
        env = np.array([np.sqrt((mono[i:i + win] ** 2).mean())
                        for i in range(0, len(mono) - win, hop_e)])
        t = (np.arange(len(env)) * hop_e + win // 2) / sr
        beat = 60.0 / args.pump_bpm
        phase = (t % beat) / beat
        nbins = 48
        curve = np.zeros(nbins)
        for b in range(nbins):
            m = (phase >= b / nbins) & (phase < (b + 1) / nbins)
            if m.any():
                curve[b] = np.median(env[m])
        # reference level = the signal's own recovered ceiling, excluding the
        # first 12% of the beat where a kick's attack transient pollutes the max
        body = curve[int(0.12 * nbins):]
        ref = np.percentile(body, 90) + 1e-12
        duck = 100 * max(0.0, 1 - curve.min() / ref)
        min_at = 100 * int(np.argmin(curve)) / nbins
        rec75 = 100 * min(1.0, curve[int(0.75 * nbins)] / ref)
        result["pump_duck_pct"] = round(float(duck), 1)
        result["pump_min_at_pct"] = round(float(min_at), 1)
        result["pump_recovery_at_75_pct"] = round(float(rec75), 1)
        if not args.json:
            print(f"pump: duck {duck:.0f}%, minimum at {min_at:.0f}% of beat, "
                  f"recovered {rec75:.0f}% by the 3/4 mark")
            bars = np.clip(curve / ref * 8, 0, 8).round().astype(int)
            print("  " + "".join(" .:-=+*#@"[v] for v in bars))
    if args.json:
        print(json.dumps(result))


if __name__ == "__main__":
    main()
