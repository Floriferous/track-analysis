"""Deep pass on a groove slice: Demucs stems, kick anatomy, sidechain pump,
hat accent contour, stereo width, cross-element microtiming, bass-note placement.

Part of the track-analysis skill. Output schema, interpretation, and failure
modes: ../references/dossier-format.md

Usage: python deep.py track.mp3 --start 1:50 --end 3:20 --out deep
Deps beyond the light pass: CPU torch + demucs (install: SKILL.md step 1).
Demucs runs through its Python API with soundfile I/O: the CLI decodes via
torchaudio->torchcodec, which requires system FFmpeg.
"""
import json
from pathlib import Path

import librosa
import librosa.display
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy.signal
import soundfile as sf

from common import band_power, beat_grid, grid16, parse_timestamp

SR = 44100
FINE_HOP = 128  # ~2.9ms


def flux_onsets(y, sr, lo, hi, delta_k=0.3):
    """One detector for every element, so cross-element comparisons share a method."""
    power = band_power(y, sr, lo, hi, FINE_HOP)
    db = librosa.power_to_db(power + 1e-10)
    flux = np.maximum(0, np.diff(db, prepend=db[0]))
    on = librosa.onset.onset_detect(onset_envelope=flux, sr=sr, hop_length=FINE_HOP, units="time",
                                    delta=max(0.5, delta_k * flux.std()), pre_max=8, post_max=8,
                                    pre_avg=16, post_avg=16, wait=8)
    return on, power


def kick_onsets(y, sr):
    amp = np.sqrt(band_power(y, sr, 25, 120, FINE_HOP))
    amp = scipy.signal.medfilt(amp, 5)
    peaks, _ = scipy.signal.find_peaks(amp, prominence=0.25 * amp.max(), distance=int(0.25 * sr / FINE_HOP))
    return librosa.frames_to_time(peaks, sr=sr, hop_length=FINE_HOP)


def kick_anatomy(y, sr, onsets, win=0.18):
    """Average lowpassed waveform, f0 glide curve, and sub decay of detected kicks."""
    sos = scipy.signal.butter(4, 250, btype="low", fs=sr, output="sos")
    ylow = scipy.signal.sosfilt(sos, y)
    n = int(win * sr)
    n_fft = 8192
    waves, f0s = [], []
    for o in onsets:
        s = int((o - 0.01) * sr)
        if s < 0 or s + n >= len(y):
            continue
        seg = ylow[s:s + n]
        waves.append(seg / (np.abs(seg).max() + 1e-9))
        f0 = []
        for fs_ in range(0, n - 1024, int(0.005 * sr)):
            fr = seg[fs_:fs_ + 1024] * np.hanning(1024)
            spec = np.abs(np.fft.rfft(fr, n_fft))
            freqs = np.fft.rfftfreq(n_fft, 1 / sr)
            i = np.argmax(spec[(freqs >= 25) & (freqs <= 250)]) + np.searchsorted(freqs, 25)
            if spec[i] < 0.01 * len(fr):
                f0.append(np.nan)
                continue
            a, b, c = spec[i - 1], spec[i], spec[i + 1]
            di = 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
            f0.append(freqs[i] + di * (freqs[1] - freqs[0]))
        f0s.append(f0)
    if not waves:
        return None, None, np.nan, 0
    avg_wave = np.array(waves).mean(axis=0)
    f0_med = np.nanmedian(np.array(f0s, dtype=float), axis=0)
    env = np.sqrt(scipy.signal.convolve(avg_wave ** 2, np.ones(441) / 441, mode="same"))
    pk = env.argmax()
    db = 20 * np.log10(env / env[pk] + 1e-9)
    below = np.where(db[pk:] < -20)[0]
    decay_ms = (below[0] / sr * 1000) if len(below) else np.nan  # nan: low end sustains into next event
    return avg_wave, f0_med, decay_ms, len(waves)


def pump_curve(y, sr, beats, ibi):
    """Mid-band (300-6k) envelope folded onto one beat cycle: the sidechain shape."""
    env = np.sqrt(band_power(y, sr, 300, 6000, FINE_HOP))
    t = librosa.frames_to_time(np.arange(len(env)), sr=sr, hop_length=FINE_HOP)
    nbin = 48
    acc, cnt = np.zeros(nbin), np.zeros(nbin)
    for b in beats:
        m = (t >= b) & (t < b + ibi)
        if m.sum() < 10:
            continue
        pos = ((t[m] - b) / ibi * nbin).astype(int) % nbin
        for p, v in zip(pos, env[m]):
            acc[p] += v
            cnt[p] += 1
    curve = acc / np.maximum(cnt, 1)
    return curve / (curve.max() + 1e-9)


def hat_accents(y, sr, beats, phase):
    """Velocity and mean offset per 16th position across all bars (hi band)."""
    on, power = flux_onsets(y, sr, 6000, 16000)
    bar_starts = beats[phase::4]
    acc, cnt, offs = np.zeros(16), np.zeros(16), [[] for _ in range(16)]
    peak = max(power.max(), 1e-12)
    for o in on:
        bi = np.searchsorted(bar_starts, o) - 1
        if bi < 0 or bi >= len(bar_starts) - 1:
            continue
        barlen = bar_starts[bi + 1] - bar_starts[bi]
        rel = (o - bar_starts[bi]) / barlen * 16
        pos = int(round(rel)) % 16
        off_ms = (rel - round(rel)) * barlen / 16 * 1000
        if abs(off_ms) > 45:
            continue
        fi = int(o * sr / FINE_HOP)
        acc[pos] += np.sqrt(power[fi:fi + 12].max() / peak)
        cnt[pos] += 1
        offs[pos].append(off_ms)
    vel = acc / np.maximum(cnt, 1)
    return vel, cnt, [float(np.mean(o)) if o else None for o in offs]


def stereo_width(stereo, sr):
    mid, side = (stereo[0] + stereo[1]) / 2, (stereo[0] - stereo[1]) / 2
    out = {}
    for name, (lo, hi) in {"sub": (25, 120), "bass": (120, 350), "low-mid": (350, 1000),
                           "mid": (1000, 4000), "high": (6000, 16000)}.items():
        m = band_power(mid, sr, lo, hi, 512).sum()
        s = band_power(side, sr, lo, hi, 512).sum()
        out[name] = float(s / (m + s + 1e-12))
    return out


def separate(stereo, sr, outdir, slug):
    """Demucs htdemucs via Python API; stems cached as wavs in outdir."""
    sources = ["drums", "bass", "other", "vocals"]
    paths = {src: outdir / f"{slug}_{src}.wav" for src in sources}
    if not all(p.exists() for p in paths.values()):
        import torch
        from demucs.apply import apply_model
        from demucs.pretrained import get_model
        model = get_model("htdemucs")
        model.eval()
        x = torch.from_numpy(stereo.astype(np.float32))
        ref = x.mean(0)
        x = (x - ref.mean()) / ref.std()
        with torch.no_grad():
            out = apply_model(model, x[None], device="cpu", progress=True)[0]
        out = out * ref.std() + ref.mean()
        for src, stem in zip(model.sources, out):
            sf.write(paths[src], stem.T.numpy(), sr)
    return {src: librosa.to_mono(sf.read(paths[src], dtype="float32")[0].T) for src in sources}


def bass_notes(y, sr, bar_starts):
    """pYIN note events on the bass stem, mapped to bar + 16th position."""
    f0, voiced, _ = librosa.pyin(y, fmin=30, fmax=300, sr=sr, frame_length=4096, hop_length=512)
    t = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=512)
    notes = []
    start = None
    for i in range(len(f0)):
        if voiced[i] and start is None:
            start = i
        elif (not voiced[i] or i == len(f0) - 1) and start is not None:
            if i - start >= 3:
                hz = float(np.nanmedian(f0[start:i]))
                n = {"t": float(t[start]), "dur": float(t[i] - t[start]), "hz": hz,
                     "note": librosa.hz_to_note(hz)}
                bi = int(np.searchsorted(bar_starts, n["t"])) - 1
                if 0 <= bi < len(bar_starts) - 1:
                    barlen = bar_starts[bi + 1] - bar_starts[bi]
                    n["bar"] = bi
                    n["pos16"] = round((n["t"] - bar_starts[bi]) / barlen * 16, 1)
                    n["dur16"] = round(n["dur"] / barlen * 16, 1)
                notes.append(n)
            start = None
    return notes


def anatomy_fig(wave, f0, decay_ms, nk, pump, out, title):
    fig, axes = plt.subplots(1, 3, figsize=(16, 4))
    axes[0].plot(np.arange(len(wave)) / SR * 1000, wave, lw=0.6)
    axes[0].set_title(f"avg kick waveform (lowpassed, n={nk})")
    axes[0].set_xlabel("ms")
    axes[1].plot(np.arange(len(f0)) * 5, f0, "o-", ms=3)
    dtxt = f"{decay_ms:.0f}ms" if np.isfinite(decay_ms) else "sustained (no -20dB drop in window)"
    axes[1].set_title(f"kick f0 glide (sub -20dB decay: {dtxt})")
    axes[1].set_xlabel("ms")
    axes[1].set_ylabel("Hz")
    duck = 100 * (1 - pump.min())
    axes[2].plot(np.linspace(0, 100, len(pump)), pump)
    axes[2].set_title(f"sidechain pump over one beat (duck {duck:.0f}%)")
    axes[2].set_xlabel("% of beat")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)


def stems_fig(stems, sr, t0, t1, out, title):
    rows = {k: v for k, v in stems.items()
            if k != "vocals" or np.sqrt((v ** 2).mean()) > 1e-3}
    fig, axes = plt.subplots(len(rows), 1, figsize=(14, 3 * len(rows)), sharex=True)
    for ax, (name, y) in zip(np.atleast_1d(axes), rows.items()):
        seg = y[int(t0 * sr):int(t1 * sr)]
        S = librosa.feature.melspectrogram(y=seg, sr=sr, n_mels=128, fmax=16000, hop_length=512)
        librosa.display.specshow(librosa.power_to_db(S, ref=np.max), sr=sr, hop_length=512,
                                 x_axis="time", y_axis="mel", fmax=16000, ax=ax, cmap="magma")
        ax.set_ylabel(name)
    np.atleast_1d(axes)[0].set_title(title)
    fig.tight_layout()
    fig.savefig(out, dpi=100)
    plt.close(fig)


def run(path, t_start, t_end, out_root):
    slug = Path(path).stem[:60]
    outdir = Path(out_root) / f"{slug}_{int(t_start)}-{int(t_end)}"
    outdir.mkdir(parents=True, exist_ok=True)
    print(f"{'=' * 70}\nDEEP: {slug} {t_start:.0f}-{t_end:.0f}s")
    stereo, _ = librosa.load(path, sr=SR, mono=False, offset=t_start, duration=t_end - t_start)
    if stereo.ndim == 1:
        stereo = np.stack([stereo, stereo])
    mix = librosa.to_mono(stereo)
    tempo, beats, ibi, phase, grid_src = beat_grid(mix, SR)
    bar_starts = beats[phase::4]
    g = grid16(beats)
    result = {"slug": slug, "t_start": t_start, "t_end": t_end, "bpm": tempo, "grid_source": grid_src}

    ko = kick_onsets(mix, SR)
    wave, f0, decay_ms, nk = kick_anatomy(mix, SR, ko)
    if nk and np.isfinite(f0).any():
        v = ~np.isnan(f0)
        f0_hi, f0_lo = float(np.nanmax(f0[v][:8])), float(np.nanmedian(f0[v][-8:]))
        print(f"{tempo:.1f} BPM | kick ({nk} avgd): f0 {f0_hi:.0f}Hz -> {f0_lo:.0f}Hz, "
              f"sub decay {'%.0fms' % decay_ms if np.isfinite(decay_ms) else 'sustained'}")
        result["kick"] = {"n": nk, "f0_start_hz": f0_hi, "f0_end_hz": f0_lo,
                          "decay_ms": decay_ms if np.isfinite(decay_ms) else None}

    pump = pump_curve(mix, SR, beats, ibi)
    result["pump"] = {"duck_pct": float(100 * (1 - pump.min())),
                      "min_at_beat_pct": float(100 * pump.argmin() / len(pump)),
                      "curve": [round(float(x), 3) for x in pump]}
    print(f"sidechain: mid-band ducks {result['pump']['duck_pct']:.0f}% "
          f"(min at {result['pump']['min_at_beat_pct']:.0f}% of beat)")

    vel, cnt, offs = hat_accents(mix, SR, beats, phase)
    result["hat_contour"] = {"vel": [round(float(x), 2) for x in vel],
                             "hits": [int(x) for x in cnt], "offset_ms": offs}
    print("hat accent contour (pos: vel / hits / offset):")
    for i in range(16):
        o = f"{offs[i]:+.0f}ms" if offs[i] is not None else "  --"
        print(f"  {i:2d}{' *beat' if i % 4 == 0 else '     '}: {'#' * int(vel[i] * 30):<30} {cnt[i]:3.0f} {o}")

    result["stereo_width_side_share"] = stereo_width(stereo, SR)
    print("stereo width (side share): " +
          ", ".join(f"{k} {v * 100:.0f}%" for k, v in result["stereo_width_side_share"].items()))

    print("separating stems (cached if present)...")
    stems = separate(stereo, SR, outdir, slug)

    elements = {
        "kick (drums lo)": (stems["drums"], 25, 150),
        "hats (drums hi)": (stems["drums"], 6000, 16000),
        "perc (drums mid)": (stems["drums"], 500, 4000),
        "bass": (stems["bass"], 30, 500),
        "synths (other)": (stems["other"], 200, 6000),
    }
    print("cross-element microtiming vs 16th grid (same detector; see trust boundaries):")
    result["microtiming"] = {}
    for name, (y, lo, hi) in elements.items():
        on, _ = flux_onsets(y, SR, lo, hi)
        offs_e = []
        for o in on:
            d = (o - g[np.argmin(np.abs(g - o))]) * 1000
            if abs(d) <= 45:
                offs_e.append(d)
        if len(offs_e) > 3:
            result["microtiming"][name] = {"hits": len(offs_e), "mean_ms": round(float(np.mean(offs_e)), 1),
                                           "sd_ms": round(float(np.std(offs_e)), 1)}
            print(f"  {name:<18} {len(offs_e):4d} hits  mean {np.mean(offs_e):+6.1f}ms  sd {np.std(offs_e):5.1f}ms")

    # report bass/stems on a 4-bar window away from the slice edges (bar 8 when available)
    nb = len(bar_starts)
    b0 = max(0, min(8, nb - 5))
    b1 = min(b0 + 4, nb - 1)
    notes = bass_notes(stems["bass"], SR, bar_starts)
    mid_bars = [n for n in notes if "bar" in n and b0 <= n["bar"] < b1]
    result["bass_notes"] = {"bars": [b0, b1], "notes": mid_bars}
    print(f"bass notes, slice bars {b0}-{b1 - 1} ({len(mid_bars)}):")
    for n in mid_bars:
        print(f"  bar {n['bar']} pos {n['pos16']:>4} len {n['dur16']:>4} 16ths  {n['note']} ({n['hz']:.0f}Hz)")

    if nk:
        anatomy_fig(wave, f0, decay_ms, nk, pump, outdir / "anatomy.png", f"{slug} {t_start:.0f}-{t_end:.0f}s")
    if nb >= 3:
        stems_fig(stems, SR, float(bar_starts[b0]), float(bar_starts[min(b0 + 2, nb - 1)]),
                  outdir / "stems.png", f"{slug} stems, slice bars {b0}-{b0 + 1}")
    (outdir / "deep.json").write_text(json.dumps(result, indent=1))
    print(f"wrote {outdir}/(deep.json, anatomy.png, stems.png)")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio")
    ap.add_argument("--start", required=True, help="slice start (M:SS or seconds); pick a main groove section")
    ap.add_argument("--end", required=True, help="slice end; 60-120s slices keep CPU Demucs fast")
    ap.add_argument("--out", default="deep", help="output root directory")
    args = ap.parse_args()
    run(args.audio, parse_timestamp(args.start), parse_timestamp(args.end), args.out)
