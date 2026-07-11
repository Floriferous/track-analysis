"""Track dossier v0: beat grid, band energies, structure, drum grids, spectrograms.

Part of the track-analysis skill. Output schema, grid notation, and known
failure modes: ../references/dossier-format.md

Usage: python ingest.py track.mp3 [track2.wav ...] --windows 1:30,3:00 --out dossier
"""
import json
from pathlib import Path

import librosa
import librosa.display
import scipy.signal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from common import beat_grid, parse_timestamp

SR = 44100
HOP = 512  # ~11.6ms global resolution
FINE_HOP = 128  # ~2.9ms for per-window microtiming

# Mel-band ranges (Hz) for band-split onset/energy analysis
BANDS = {
    "sub/kick (25-120Hz)": (25, 120),
    "bass (120-350Hz)": (120, 350),
    "low-mid (350-1k)": (350, 1000),
    "mid (1k-4k)": (1000, 4000),
    "high/hats (6k-16k)": (6000, 16000),
}

KRUMHANSL_MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KRUMHANSL_MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def band_envelopes(y, sr, hop):
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop)) ** 2
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
    envs = {}
    for name, (lo, hi) in BANDS.items():
        idx = (freqs >= lo) & (freqs < hi)
        band_power = S[idx].sum(axis=0)
        envs[name] = band_power
    return envs


def onset_env_from_power(power):
    db = librosa.power_to_db(power + 1e-10)
    diff = np.maximum(0.0, np.diff(db, prepend=db[0]))
    return diff


def estimate_key(y, sr):
    """Essentia's key extractor when installed (reliably beats chroma templates);
    chroma-template fallback otherwise. Cross-check against the transcribed bass root."""
    try:
        import essentia.standard as es
        key, scale, strength = es.KeyExtractor()(y.astype(np.float32))
        return f"{key} {scale} (essentia {strength:.2f})"
    except ImportError:
        pass
    except Exception as e:  # installed but broken -> degrade to chroma
        print(f"essentia key extraction failed ({e}); using chroma fallback")
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
    best = None
    for mode, profile in (("major", KRUMHANSL_MAJ), ("minor", KRUMHANSL_MIN)):
        for shift in range(12):
            r = np.corrcoef(np.roll(profile, shift), chroma)[0, 1]
            if best is None or r > best[0]:
                best = (r, NOTE_NAMES[shift], mode)
    return f"{best[1]} {best[2]} (chroma r={best[0]:.2f}, weak)"


def loudness_metrics(path):
    """EBU R128 loudness + dynamics on the stereo file; None if pyloudnorm absent."""
    try:
        import pyloudnorm as pyln
    except ImportError:
        return None
    y, sr = librosa.load(path, sr=SR, mono=False)
    stereo = y.T if y.ndim == 2 else y[:, None]
    meter = pyln.Meter(sr)
    st = []
    for s in range(0, stereo.shape[0] - 3 * sr, sr):
        st.append(meter.integrated_loudness(stereo[s:s + 3 * sr]))
    st = np.array(st)
    st = st[np.isfinite(st) & (st > -70)]
    mono = stereo.mean(axis=1)
    peak_db = 20 * np.log10(np.abs(stereo).max() + 1e-12)
    rms_db = 20 * np.log10(np.sqrt((mono ** 2).mean()) + 1e-12)
    return {
        "integrated_lufs": round(float(meter.integrated_loudness(stereo)), 1),
        "short_term_max_lufs": round(float(st.max()), 1) if len(st) else None,
        "short_term_range_lu": round(float(np.percentile(st, 95) - np.percentile(st, 10)), 1) if len(st) else None,
        "sample_peak_dbfs": round(float(peak_db), 1),
        "crest_db": round(float(peak_db - rms_db), 1),
    }


def structure_boundaries(bar_band_matrix, bar_times, min_gap_bars=8):
    """Change-point detection on per-bar band-energy profile."""
    M = bar_band_matrix / (np.linalg.norm(bar_band_matrix, axis=1, keepdims=True) + 1e-10)
    n = len(M)
    w = 4
    novelty = np.zeros(n)
    for i in range(w, n - w):
        before = M[i - w:i].mean(axis=0)
        after = M[i:i + w].mean(axis=0)
        novelty[i] = 1 - np.dot(before, after) / (np.linalg.norm(before) * np.linalg.norm(after) + 1e-10)
    thresh = novelty.mean() + 1.2 * novelty.std()
    bounds = []
    for i in range(w, n - w):
        if novelty[i] >= thresh and novelty[i] == novelty[max(0, i - min_gap_bars):i + min_gap_bars].max():
            bounds.append(i)
    return bounds, novelty


def fmt_time(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"


def drum_grid(y, sr, beat_times, center_sec, n_bars, bar_starts):
    """16th-note grid of band onsets for n_bars around center_sec."""
    # find bar containing center
    bar_idx = int(np.searchsorted(bar_starts, center_sec)) - 1
    bar_idx = max(0, min(bar_idx, len(bar_starts) - n_bars - 1))
    t0, t1 = bar_starts[bar_idx], bar_starts[bar_idx + n_bars]
    pad = 0.1
    s0, s1 = int((t0 - pad) * sr), int((t1 + pad) * sr)
    seg = y[max(0, s0):s1]
    envs = band_envelopes(seg, sr, FINE_HOP)
    times_off = (t0 - pad) if s0 >= 0 else 0.0

    # 16th grid from beat times within window
    beats_in = beat_times[(beat_times >= t0 - 0.05) & (beat_times <= t1 + 0.5)]
    grid = []
    for i in range(len(beats_in) - 1):
        for k in range(4):
            grid.append(beats_in[i] + (beats_in[i + 1] - beats_in[i]) * k / 4)
    grid = np.array([g for g in grid if t0 - 0.03 <= g < t1 - 0.01])

    out = {}
    for name, power in envs.items():
        if name.startswith("sub"):
            # Sustained sub bass masks flux onsets; kicks are amplitude peaks instead.
            amp = np.sqrt(power)
            amp = scipy.signal.medfilt(amp, 5)
            peaks, _ = scipy.signal.find_peaks(
                amp, prominence=0.12 * amp.max(), distance=int(0.12 * sr / FINE_HOP))
            onsets = librosa.frames_to_time(peaks, sr=sr, hop_length=FINE_HOP) + times_off
        else:
            env = onset_env_from_power(power)
            onsets = librosa.onset.onset_detect(
                onset_envelope=env, sr=sr, hop_length=FINE_HOP, units="time",
                delta=max(0.5, 0.3 * env.std()), pre_max=8, post_max=8, pre_avg=16, post_avg=16, wait=8,
            ) + times_off
        onsets = onsets[(onsets >= t0 - 0.03) & (onsets < t1)]
        # strength at each onset (normalized within window)
        peak = power.max() + 1e-10
        hits = []
        for o in onsets:
            fi = int((o - times_off) * sr / FINE_HOP)
            vel = float(np.sqrt(power[fi:fi + 12].max() / peak))
            gi = int(np.argmin(np.abs(grid - o)))
            offset_ms = float((o - grid[gi]) * 1000)
            hits.append({"t": float(o), "grid16": gi, "offset_ms": round(offset_ms, 1), "vel": round(vel, 2)})
        out[name] = hits
    return out, t0, t1, grid, bar_idx


def render_grid_text(grids, n_bars):
    lines = []
    n16 = n_bars * 16
    for name, hits in grids.items():
        row = ["."] * n16
        for h in hits:
            if 0 <= h["grid16"] < n16 and abs(h["offset_ms"]) < 40:
                v = h["vel"]
                row[h["grid16"]] = "X" if v > 0.75 else ("x" if v > 0.45 else "o")
        bars = ["".join(row[b * 16:(b + 1) * 16]) for b in range(n_bars)]
        lines.append(f"{name:<22} |" + "|".join(bars) + "|")
    return "\n".join(lines)


def spectrogram_png(y, sr, t0, t1, path, title, beat_times=None):
    seg = y[int(t0 * sr):int(t1 * sr)]
    S = librosa.feature.melspectrogram(y=seg, sr=sr, n_mels=160, fmax=16000, hop_length=HOP)
    fig, ax = plt.subplots(figsize=(14, 6))
    img = librosa.display.specshow(
        librosa.power_to_db(S, ref=np.max), sr=sr, hop_length=HOP,
        x_axis="time", y_axis="mel", fmax=16000, ax=ax, cmap="magma",
    )
    ax.set_yticks([50, 100, 200, 400, 800, 1600, 3200, 6400, 12800])
    if beat_times is not None:
        for b in beat_times[(beat_times >= t0) & (beat_times < t1)]:
            ax.axvline(b - t0, color="cyan", alpha=0.25, lw=0.6)
    ax.set_title(title)
    fig.colorbar(img, ax=ax, format="%d dB")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def overview_png(bar_matrix, bar_starts, bounds, path, title):
    fig, ax = plt.subplots(figsize=(16, 5))
    M = bar_matrix.T
    M = M / (M.max(axis=1, keepdims=True) + 1e-10)
    ax.imshow(M, aspect="auto", origin="lower", cmap="magma", interpolation="nearest")
    ax.set_yticks(range(len(BANDS)))
    ax.set_yticklabels(list(BANDS.keys()))
    tick_bars = range(0, len(bar_starts) - 1, 16)
    ax.set_xticks(list(tick_bars))
    ax.set_xticklabels([f"bar {b}\n{fmt_time(bar_starts[b])}" for b in tick_bars], fontsize=7)
    for b in bounds:
        ax.axvline(b - 0.5, color="cyan", lw=1.2)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def analyze(path, out_root, windows_sec):
    slug = Path(path).stem[:60]
    out = Path(out_root) / slug
    out.mkdir(parents=True, exist_ok=True)
    print(f"\n{'=' * 80}\nTRACK: {slug}")
    y, sr = librosa.load(path, sr=SR, mono=True)
    dur = len(y) / sr
    print(f"duration: {fmt_time(dur)}")

    tempo, beats, _, phase, grid_src = beat_grid(y, sr)
    ibis = np.diff(beats)
    print(f"tempo: {tempo:.1f} BPM | beats: {len(beats)} | IBI median {np.median(ibis)*1000:.1f}ms "
          f"std {ibis.std()*1000:.1f}ms | grid: {grid_src}")
    bar_starts = beats[phase::4]
    print(f"bars: {len(bar_starts)} (phase {phase})")

    envs_g = band_envelopes(y, sr, HOP)

    # per-bar band energy matrix
    frame_t = librosa.frames_to_time(np.arange(len(envs_g[list(BANDS)[0]])), sr=sr, hop_length=HOP)
    bar_matrix = np.zeros((len(bar_starts) - 1, len(BANDS)))
    for bi in range(len(bar_starts) - 1):
        mask = (frame_t >= bar_starts[bi]) & (frame_t < bar_starts[bi + 1])
        for j, name in enumerate(BANDS):
            bar_matrix[bi, j] = np.sqrt(envs_g[name][mask].mean() + 1e-12)

    bounds, novelty = structure_boundaries(bar_matrix, bar_starts)
    print("section boundaries (bar / time):", ", ".join(f"bar {b} @ {fmt_time(bar_starts[b])}" for b in bounds))

    key = estimate_key(y, sr)
    loudness = loudness_metrics(path)
    if loudness:
        print(f"loudness: {loudness['integrated_lufs']:.1f} LUFS integrated | "
              f"short-term max {loudness['short_term_max_lufs']:.1f} | crest {loudness['crest_db']:.1f} dB")
    print(f"key estimate: {key}")

    overview_png(bar_matrix, bar_starts, bounds, out / "overview.png", f"{slug} — band energy per bar, {tempo:.1f} BPM")

    dossier = {
        "slug": slug, "duration_sec": dur, "bpm": tempo, "key": key,
        "grid_source": grid_src, "loudness": loudness,
        "n_bars": len(bar_starts),
        "bar_starts": [round(float(t), 3) for t in bar_starts],
        "boundaries": [{"bar": int(b), "time": round(float(bar_starts[b]), 2)} for b in bounds],
        "windows": {},
    }

    n_bars_win = min(4, len(bar_starts) - 1)
    for w in windows_sec:
        grids, t0, t1, grid, bar_idx = drum_grid(y, sr, beats, w, n_bars_win, bar_starts)
        label = f"{int(w // 60)}m{int(w % 60):02d}s"
        print(f"\n-- window @{label}: bars {bar_idx}-{bar_idx + n_bars_win} ({fmt_time(t0)}–{fmt_time(t1)}) --")
        print(render_grid_text(grids, n_bars_win))
        for name, hits in grids.items():
            on_grid = [h for h in hits if abs(h["offset_ms"]) < 40]
            if on_grid:
                offs = [h["offset_ms"] for h in on_grid]
                print(f"   {name}: {len(on_grid)} hits, offset mean {np.mean(offs):+.1f}ms sd {np.std(offs):.1f}ms")
        spectrogram_png(y, sr, t0, t1, out / f"spec_{label}.png",
                        f"{slug} @ {label} (bars {bar_idx}-{bar_idx + n_bars_win})", beats)
        dossier["windows"][label] = {"t0": round(t0, 2), "t1": round(t1, 2), "bar": bar_idx, "grids": grids}

    (out / "dossier.json").write_text(json.dumps(dossier, indent=1))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio", nargs="+", help="audio file(s): wav/mp3/flac/ogg")
    ap.add_argument("--windows", default="1:30,3:00",
                    help="comma-separated timestamps to slice (M:SS or seconds)")
    ap.add_argument("--out", default="dossier", help="output root directory")
    args = ap.parse_args()
    windows = [parse_timestamp(w) for w in args.windows.split(",")]
    for path in args.audio:
        analyze(path, args.out, windows)
