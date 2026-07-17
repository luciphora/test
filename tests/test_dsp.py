import math

import numpy as np
import pytest

from pipeline import dsp

SR = 48000


def sine(freq, seconds, amp=1.0, sr=SR):
    t = np.arange(int(seconds * sr)) / sr
    return amp * np.sin(2 * math.pi * freq * t)


def test_integrated_lufs_reference_tone():
    # BS.1770: a 997 Hz stereo sine at -23 dBFS measures -23 LUFS (±0.2)
    x = dsp.to_stereo(sine(997, 10, amp=dsp.db_to_lin(-23)))
    assert dsp.integrated_lufs(x, SR) == pytest.approx(-23.0, abs=0.2)


def test_lufs_tracks_gain():
    x = dsp.to_stereo(sine(997, 10, amp=dsp.db_to_lin(-23)))
    base = dsp.integrated_lufs(x, SR)
    assert dsp.integrated_lufs(x * dsp.db_to_lin(-6), SR) == pytest.approx(base - 6, abs=0.1)


def test_highpass_attenuates_low_passes_high():
    b, a = dsp.biquad_highpass(75, SR)
    low = dsp.apply_biquad(sine(30, 3), b, a)
    high = dsp.apply_biquad(sine(1000, 3), b, a)
    assert dsp.rms_dbfs(low[SR:]) < dsp.rms_dbfs(sine(30, 3)[SR:]) - 12
    assert abs(dsp.rms_dbfs(high[SR:]) - dsp.rms_dbfs(sine(1000, 3)[SR:])) < 0.5


def test_peaking_cut_depth():
    b, a = dsp.biquad_peaking(250, SR, -1.5, 1.2)
    y = dsp.apply_biquad(sine(250, 3), b, a)
    assert dsp.rms_dbfs(y[SR:2 * SR]) == pytest.approx(
        dsp.rms_dbfs(sine(250, 3)[SR:2 * SR]) - 1.5, abs=0.2)


def test_true_peak_exceeds_sample_peak_on_intersample():
    x = sine(11997, 1, amp=0.99)
    assert dsp.true_peak_dbtp(x, SR) >= dsp.peak_dbfs(x) - 0.1


def test_compressor_hits_target_gr():
    speech_like = sine(200, 5, amp=0.5) * (0.4 + 0.6 * np.abs(np.sin(
        2 * math.pi * 1.5 * np.arange(5 * SR) / SR)))
    y, info = dsp.compress(speech_like, SR, ratio=2.0, target_gr_db=3.0)
    assert info["gr_p95_db"] == pytest.approx(3.0, abs=0.5)
    assert len(y) == len(speech_like)


def test_duck_reduction_capped():
    stem = sine(240, 10, amp=0.1)
    key = np.zeros(10 * SR)
    key[2 * SR:8 * SR] = sine(400, 6, amp=0.3)
    ducked, info = dsp.duck(stem, key, SR, gr_db=1.5, attack_ms=50, release_ms=800)
    assert 0 < info["max_gr_applied_db"] <= 2.0
    mid = slice(4 * SR, 6 * SR)
    assert dsp.rms_dbfs(ducked[mid]) == pytest.approx(dsp.rms_dbfs(stem[mid]) - 1.5, abs=0.3)
    head = slice(0, int(1.5 * SR))
    assert dsp.rms_dbfs(ducked[head]) == pytest.approx(dsp.rms_dbfs(stem[head]), abs=0.3)


def test_slice_on_silences():
    gap = np.zeros(int(0.6 * SR))
    stmt = sine(300, 1.0, amp=0.3)
    audio = np.concatenate([stmt, gap, stmt, gap, stmt])
    pieces = dsp.slice_on_silences(audio, SR, threshold_db=-45, min_silence_s=0.4)
    assert len(pieces) == 3


def test_brown_noise_level():
    n = dsp.brown_noise(5 * SR, rms_db=-68.0, seed=1)
    assert dsp.rms_dbfs(n) == pytest.approx(-68.0, abs=0.5)
