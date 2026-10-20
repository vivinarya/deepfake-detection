import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from rppg_engine import bandpass_filter

def test_bandpass_filter_attenuates_out_of_band():
    fs = 30.0
    duration = 5.0
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)

    # 1.2 Hz (72 BPM - valid cardiac frequency band)
    cardiac_signal = np.sin(2 * np.pi * 1.2 * t)
    # 0.1 Hz (drift/respiratory motion - below 0.7 Hz passband)
    low_freq_drift = 2.0 * np.sin(2 * np.pi * 0.1 * t)
    # 6.0 Hz (high frequency sensor noise - above 3.0 Hz passband)
    high_freq_noise = 2.0 * np.sin(2 * np.pi * 6.0 * t)

    composite = cardiac_signal + low_freq_drift + high_freq_noise
    filtered = bandpass_filter(composite, fs=fs, low=0.7, high=3.0)

    correlation = np.corrcoef(filtered, cardiac_signal)[0, 1]
    assert correlation > 0.85, f"Expected cardiac correlation > 0.85, got {correlation:.3f}"

def test_analyze_video_nonexistent_file_raises():
    from rppg_engine import analyze_video_rppg
    with pytest.raises(Exception):
        analyze_video_rppg("non_existent_dummy_file.mp4")
