"""Shared: timestamp parsing, band power, and the beat/bar grid.

Grid source: Beat This! (arXiv:2407.21658) when installed — model-predicted beats
AND downbeats, no phase heuristics. Fallback: librosa beat tracking with phase
re-anchored to the kick band. The source used is returned so reports can state it.
"""
import librosa
import numpy as np

_audio2beats = None


def parse_timestamp(s):
    return sum(float(p) * 60 ** i for i, p in enumerate(reversed(s.strip().split(":"))))


def fmt_label(t):
    """Seconds -> filesystem-safe M:SS label, e.g. 227 -> '3m47s'."""
    return f"{int(t // 60)}m{int(t % 60):02d}s"


def band_power(y, sr, lo, hi, hop, n_fft=2048):
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop)) ** 2
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    return S[(freqs >= lo) & (freqs < hi)].sum(axis=0)


def _librosa_grid(y, sr):
    """(tempo, beats, phase) — beat phase re-anchored to kick-band onset energy."""
    oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
    tempo, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=512, units="time", trim=False)
    ibi = float(np.median(np.diff(beats)))
    kick = band_power(y, sr, 25, 120, 512)
    flux = np.maximum(0, np.diff(librosa.power_to_db(kick + 1e-10), prepend=0))

    def score(times):
        fr = (times * sr / 512).astype(int)
        fr = fr[(fr > 0) & (fr < len(flux) - 1)]
        if not len(fr):
            return 0.0
        return np.mean([flux[f - 1:f + 2].max() for f in fr])

    best = max([0.0, ibi / 2, ibi / 4, -ibi / 4], key=lambda s: score(beats + s))
    beats = beats + best
    phase = int(np.argmax([score(beats[p::4]) for p in range(4)]))
    return float(np.atleast_1d(tempo)[0]), beats, phase


def beat_grid(y, sr):
    """Beat/bar grid for steady-tempo 4/4 material.

    Returns (tempo_bpm, beats, ibi, phase, source); bar starts are beats[phase::4].
    """
    global _audio2beats
    try:
        from beat_this.inference import Audio2Beats
        if _audio2beats is None:
            _audio2beats = Audio2Beats(checkpoint_path="final0", device="cpu", dbn=False)
        y22 = librosa.resample(y, orig_sr=sr, target_sr=22050)
        beats, downbeats = _audio2beats(y22, 22050)
        if len(beats) >= 8 and len(downbeats) >= 2:
            ibi = float(np.median(np.diff(beats)))
            phase = int(np.argmin(np.abs(beats - downbeats[0]))) % 4
            return 60.0 / ibi, np.asarray(beats), ibi, phase, "beat_this"
    except ImportError:
        pass
    except Exception as e:  # installed but broken (checkpoint fetch, odd audio) -> degrade, don't crash
        print(f"beat_this failed ({e}); falling back to librosa grid")
    tempo, beats, phase = _librosa_grid(y, sr)
    return tempo, beats, float(np.median(np.diff(beats))), phase, "librosa+kick-anchor"


def grid16(beats):
    """16th-note grid interpolated between beats."""
    g = []
    for i in range(len(beats) - 1):
        for k in range(4):
            g.append(beats[i] + (beats[i + 1] - beats[i]) * k / 4)
    return np.array(g)
