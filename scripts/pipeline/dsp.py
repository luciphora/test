"""Numpy-only DSP toolbox: filters, loudness (BS.1770-4), dynamics, edits.

Design notes:
- Biquads are applied as truncated impulse responses via FFT overlap-add,
  which keeps the dependency set to numpy while staying fast on 30-minute
  buffers. 16k taps puts truncation error far below the noise floor for the
  gentle EQ/HPF curves used here.
- Envelope followers run at a 5 ms control rate (vectorized RMS, then a
  short sequential smoothing loop), interpolated back to sample rate.
- Loudness is BS.1770-4 integrated (K-weighting + absolute/relative gating),
  valid at 48 kHz; other rates are resampled for measurement.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import soundfile as sf
import soxr

FIR_TAPS = 16384
CONTROL_HOP_S = 0.005


# -- io ----------------------------------------------------------------------

def read_wav(path: Path) -> tuple[np.ndarray, int]:
    """Returns (float64 array shaped (n,) mono or (n, ch), sample_rate)."""
    data, sr = sf.read(str(path), always_2d=False)
    return np.asarray(data, dtype=np.float64), sr


def write_wav(path: Path, data: np.ndarray, sr: int, bit_depth: int = 24) -> None:
    subtype = {16: "PCM_16", 24: "PCM_24", 32: "PCM_32"}[bit_depth]
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.clip(data, -1.0, 1.0), sr, subtype=subtype)


def pcm16le_to_float(raw: bytes) -> np.ndarray:
    return np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0


def resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return x
    return np.asarray(soxr.resample(x, sr_in, sr_out, quality="VHQ"), dtype=np.float64)


def to_stereo(x: np.ndarray) -> np.ndarray:
    if x.ndim == 1:
        return np.stack([x, x], axis=-1)
    return x


def mono(x: np.ndarray) -> np.ndarray:
    return x if x.ndim == 1 else x.mean(axis=-1)


# -- levels --------------------------------------------------------------------

def db_to_lin(db: float) -> float:
    return 10.0 ** (db / 20.0)


def lin_to_db(x: float) -> float:
    return -math.inf if x <= 0 else 20.0 * math.log10(x)


def peak_dbfs(x: np.ndarray) -> float:
    return lin_to_db(float(np.max(np.abs(x))) if x.size else 0.0)


def rms_dbfs(x: np.ndarray) -> float:
    return -math.inf if x.size == 0 else lin_to_db(float(np.sqrt(np.mean(x ** 2))))


def true_peak_dbtp(x: np.ndarray, sr: int) -> float:
    x2 = x if x.ndim == 1 else x.reshape(-1, x.shape[-1])
    over = resample(x2, sr, sr * 4)
    return peak_dbfs(over)


# -- biquads (RBJ cookbook), applied as FIR via FFT overlap-add ---------------

def _biquad_impulse(b: np.ndarray, a: np.ndarray, taps: int = FIR_TAPS) -> np.ndarray:
    h = np.zeros(taps)
    x = np.zeros(taps)
    x[0] = 1.0
    # direct form I on the impulse only (short loop, taps not samples)
    for n in range(taps):
        h[n] = (b[0] * x[n]
                + (b[1] * x[n - 1] if n >= 1 else 0.0)
                + (b[2] * x[n - 2] if n >= 2 else 0.0)
                - (a[1] * h[n - 1] if n >= 1 else 0.0)
                - (a[2] * h[n - 2] if n >= 2 else 0.0))
    return h


def fft_convolve(x: np.ndarray, h: np.ndarray) -> np.ndarray:
    """Linear convolution via FFT, trimmed to len(x) (filter delay preserved)."""
    n = len(x) + len(h) - 1
    nfft = 1 << (n - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(h, nfft), nfft)
    return y[: len(x)]


def apply_biquad(x: np.ndarray, b: np.ndarray, a: np.ndarray) -> np.ndarray:
    h = _biquad_impulse(np.asarray(b, float), np.asarray(a, float))
    if x.ndim == 1:
        return fft_convolve(x, h)
    return np.stack([fft_convolve(x[:, c], h) for c in range(x.shape[-1])], axis=-1)


def biquad_highpass(fc: float, sr: int, q: float = 0.7071) -> tuple[np.ndarray, np.ndarray]:
    w0 = 2 * math.pi * fc / sr
    alpha = math.sin(w0) / (2 * q)
    cw = math.cos(w0)
    b = np.array([(1 + cw) / 2, -(1 + cw), (1 + cw) / 2])
    a = np.array([1 + alpha, -2 * cw, 1 - alpha])
    return b / a[0], a / a[0]


def biquad_lowpass(fc: float, sr: int, q: float = 0.7071) -> tuple[np.ndarray, np.ndarray]:
    w0 = 2 * math.pi * fc / sr
    alpha = math.sin(w0) / (2 * q)
    cw = math.cos(w0)
    b = np.array([(1 - cw) / 2, 1 - cw, (1 - cw) / 2])
    a = np.array([1 + alpha, -2 * cw, 1 - alpha])
    return b / a[0], a / a[0]


def biquad_peaking(fc: float, sr: int, gain_db: float, q: float) -> tuple[np.ndarray, np.ndarray]:
    A = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * fc / sr
    alpha = math.sin(w0) / (2 * q)
    cw = math.cos(w0)
    b = np.array([1 + alpha * A, -2 * cw, 1 - alpha * A])
    a = np.array([1 + alpha / A, -2 * cw, 1 - alpha / A])
    return b / a[0], a / a[0]


# -- loudness (ITU-R BS.1770-4) ------------------------------------------------

# K-weighting coefficients, defined at 48 kHz
_K_SHELF_B = np.array([1.53512485958697, -2.69169618940638, 1.19839281085285])
_K_SHELF_A = np.array([1.0, -1.69065929318241, 0.73248077421585])
_K_HPF_B = np.array([1.0, -2.0, 1.0])
_K_HPF_A = np.array([1.0, -1.99004745483398, 0.99007225036621])


def k_weight(x: np.ndarray, sr: int) -> tuple[np.ndarray, int]:
    if sr != 48000:
        x = resample(x, sr, 48000)
        sr = 48000
    y = apply_biquad(x, _K_SHELF_B, _K_SHELF_A)
    y = apply_biquad(y, _K_HPF_B, _K_HPF_A)
    return y, sr


def integrated_lufs(x: np.ndarray, sr: int) -> float:
    """BS.1770-4 integrated loudness with absolute (-70) and relative (-10) gates."""
    x = to_stereo(x) if x.ndim == 1 else x
    y, sr = k_weight(x, sr)
    block = int(0.400 * sr)
    hop = int(0.100 * sr)
    if len(y) < block:
        return -math.inf
    n_blocks = 1 + (len(y) - block) // hop
    idx = np.arange(block)[None, :] + hop * np.arange(n_blocks)[:, None]
    # channel weights are 1.0 for L/R
    power = (y[:, 0][idx] ** 2).mean(axis=1) + (y[:, 1][idx] ** 2).mean(axis=1) \
        if y.ndim == 2 else 2 * (y[idx] ** 2).mean(axis=1)
    loud = -0.691 + 10 * np.log10(np.maximum(power, 1e-20))
    gated = loud > -70.0
    if not gated.any():
        return -math.inf
    rel_gate = (-0.691 + 10 * np.log10(power[gated].mean())) - 10.0
    keep = gated & (loud > rel_gate)
    if not keep.any():
        return -math.inf
    return float(-0.691 + 10 * np.log10(power[keep].mean()))


# -- envelopes & dynamics --------------------------------------------------------

def control_rms_db(x: np.ndarray, sr: int, hop_s: float = CONTROL_HOP_S) -> np.ndarray:
    """RMS level in dBFS at the control rate (one value per hop)."""
    xm = mono(x)
    hop = max(1, int(hop_s * sr))
    n = len(xm) // hop
    frames = xm[: n * hop].reshape(n, hop)
    rms = np.sqrt((frames ** 2).mean(axis=1))
    return 20 * np.log10(np.maximum(rms, 1e-10))


def smooth_attack_release(ctrl: np.ndarray, attack_hops: float, release_hops: float,
                          rising_is_attack: bool = True) -> np.ndarray:
    """One-pole attack/release smoothing on a control-rate signal."""
    ca = math.exp(-1.0 / max(attack_hops, 1e-6))
    cr = math.exp(-1.0 / max(release_hops, 1e-6))
    out = np.empty_like(ctrl)
    state = ctrl[0]
    for i, v in enumerate(ctrl):
        rising = v > state
        coef = (ca if rising else cr) if rising_is_attack else (cr if rising else ca)
        state = coef * state + (1 - coef) * v
        out[i] = state
    return out


def expand_control(ctrl: np.ndarray, total_samples: int, sr: int,
                   hop_s: float = CONTROL_HOP_S) -> np.ndarray:
    hop = max(1, int(hop_s * sr))
    t_ctrl = np.arange(len(ctrl)) * hop + hop / 2
    return np.interp(np.arange(total_samples), t_ctrl, ctrl)


def compress(x: np.ndarray, sr: int, ratio: float, target_gr_db: float,
             attack_ms: float = 10.0, release_ms: float = 120.0) -> tuple[np.ndarray, dict]:
    """Feed-forward compressor; threshold auto-set so the 95th-percentile gain
    reduction over speech-active regions lands near target_gr_db."""
    lvl = control_rms_db(x, sr)
    hops_per_s = 1.0 / CONTROL_HOP_S
    env = smooth_attack_release(lvl, attack_ms / 1000 * hops_per_s,
                                release_ms / 1000 * hops_per_s)
    active = env > -45.0

    def gr_at(threshold: float) -> np.ndarray:
        over = np.maximum(env - threshold, 0.0)
        return over * (1 - 1 / ratio)

    lo, hi = -80.0, 0.0
    for _ in range(40):
        mid = (lo + hi) / 2
        gr = gr_at(mid)
        stat = np.percentile(gr[active], 95) if active.any() else 0.0
        if stat > target_gr_db:
            lo = mid
        else:
            hi = mid
    threshold = (lo + hi) / 2
    gr_ctrl = gr_at(threshold)
    gain = expand_control(-gr_ctrl, len(mono(x)), sr)
    gain_lin = 10 ** (gain / 20)
    y = x * gain_lin if x.ndim == 1 else x * gain_lin[:, None]
    info = {"threshold_dbfs": round(threshold, 2), "ratio": ratio,
            "gr_p95_db": round(float(np.percentile(gr_ctrl[active], 95)) if active.any() else 0.0, 2)}
    return y, info


def deess(x: np.ndarray, sr: int, split_hz: float = 5500.0,
          max_reduction_db: float = 3.0) -> np.ndarray:
    """Light de-esser: compress the high band when it spikes above its norm."""
    xm = x
    b, a = biquad_lowpass(split_hz, sr)
    low = apply_biquad(xm, b, a)
    high = xm - low
    lvl = control_rms_db(high, sr)
    active = lvl > -60
    if not active.any():
        return x
    norm = float(np.percentile(lvl[active], 60))
    hops_per_s = 1.0 / CONTROL_HOP_S
    env = smooth_attack_release(lvl, 0.002 * hops_per_s * 1000 / 1000,
                                0.080 * hops_per_s * 1000 / 1000)
    over = np.clip(env - (norm + 4.0), 0.0, None)
    gr = np.minimum(over * 0.7, max_reduction_db)
    gain = 10 ** (expand_control(-gr, len(xm), sr) / 20)
    return low + high * gain


def duck(stem: np.ndarray, key: np.ndarray, sr: int, gr_db: float,
         attack_ms: float, release_ms: float, max_gr_db: float = 2.0,
         active_threshold_db: float = -45.0) -> tuple[np.ndarray, dict]:
    """Duck `stem` under active regions of `key` (narration)."""
    lvl = control_rms_db(key, sr)
    target = np.where(lvl > active_threshold_db, min(gr_db, max_gr_db), 0.0)
    hops_per_s = 1.0 / CONTROL_HOP_S
    env = smooth_attack_release(target, attack_ms / 1000 * hops_per_s,
                                release_ms / 1000 * hops_per_s)
    env = np.minimum(env, max_gr_db)
    n = len(stem) if stem.ndim == 1 else stem.shape[0]
    gain = 10 ** (expand_control(-env, n, sr) / 20)
    out = stem * gain if stem.ndim == 1 else stem * gain[:, None]
    return out, {"max_gr_applied_db": round(float(env.max()), 2)}


# -- edits, fades, noise ---------------------------------------------------------

def raised_cosine_fade(n: int, direction: str) -> np.ndarray:
    t = np.linspace(0, math.pi / 2, n)
    curve = np.sin(t) ** 2
    return curve if direction == "in" else curve[::-1]


def fade_edges(x: np.ndarray, sr: int, fade_s: float) -> np.ndarray:
    n = min(int(fade_s * sr), len(x) // 2)
    if n <= 0:
        return x
    y = x.copy()
    fin = raised_cosine_fade(n, "in")
    fout = raised_cosine_fade(n, "out")
    if y.ndim == 1:
        y[:n] *= fin
        y[-n:] *= fout
    else:
        y[:n] *= fin[:, None]
        y[-n:] *= fout[:, None]
    return y


def brown_noise(n: int, rms_db: float, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    white = rng.standard_normal(n + 4800)
    brown = np.cumsum(white)
    brown -= np.linspace(brown[0], brown[-1], len(brown))  # detrend
    brown = brown[4800:] if len(brown) > n else brown[:n]
    brown = brown[:n]
    cur = np.sqrt(np.mean(brown ** 2))
    return brown * (db_to_lin(rms_db) / max(cur, 1e-12))


def find_silences(x: np.ndarray, sr: int, threshold_db: float,
                  min_len_s: float) -> list[tuple[int, int]]:
    """Sample ranges where the control-rate RMS stays below threshold."""
    lvl = control_rms_db(x, sr)
    hop = max(1, int(CONTROL_HOP_S * sr))
    quiet = lvl < threshold_db
    silences = []
    start = None
    for i, q in enumerate([*quiet, False]):
        if q and start is None:
            start = i
        elif not q and start is not None:
            if (i - start) * CONTROL_HOP_S >= min_len_s:
                silences.append((start * hop, i * hop))
            start = None
    return silences


def slice_on_silences(x: np.ndarray, sr: int, threshold_db: float = -45.0,
                      min_silence_s: float = 0.4, pad_s: float = 0.05) -> list[np.ndarray]:
    """Split audio into statements separated by qualifying silences."""
    silences = find_silences(x, sr, threshold_db, min_silence_s)
    pad = int(pad_s * sr)
    bounds = [0]
    for s0, s1 in silences:
        bounds.append((s0 + s1) // 2)
    bounds.append(len(x))
    out = []
    for b0, b1 in zip(bounds[:-1], bounds[1:]):
        seg = x[max(0, b0 - pad): min(len(x), b1 + pad)]
        if rms_dbfs(seg) > threshold_db:  # drop pure-silence segments
            out.append(fade_edges(seg, sr, 0.01))
    return out


# -- analysis helpers for stage verification --------------------------------------

def fft_peak_hz(x: np.ndarray, sr: int) -> float:
    xm = mono(x)
    n = min(len(xm), sr * 30)
    seg = xm[len(xm) // 2 - n // 2: len(xm) // 2 + n // 2]
    win = np.hanning(len(seg))
    spec = np.abs(np.fft.rfft(seg * win))
    freqs = np.fft.rfftfreq(len(seg), 1 / sr)
    return float(freqs[int(np.argmax(spec))])


def envelope_rate_hz(x: np.ndarray, sr: int) -> float:
    """Dominant modulation rate of the amplitude envelope."""
    xm = np.abs(mono(x))
    b, a = biquad_lowpass(30.0, sr)
    env = apply_biquad(xm, b, a)
    n = min(len(env), sr * 60)
    seg = env[len(env) // 2 - n // 2: len(env) // 2 + n // 2]
    seg = seg - seg.mean()
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    freqs = np.fft.rfftfreq(len(seg), 1 / sr)
    keep = freqs > 0.5  # ignore DC / drift
    return float(freqs[keep][int(np.argmax(spec[keep]))])
