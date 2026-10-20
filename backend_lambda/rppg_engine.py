import cv2
import numpy as np
import mediapipe as mp
from scipy.signal import butter, filtfilt, welch

# MediaPipe FaceMesh landmark indices for the 3 biological ROIs
ROI_LANDMARKS = {
    "forehead": [10, 338, 297, 332, 284, 251, 21, 54, 103, 67, 109],
    "left_cheek": [117, 118, 101, 36, 205, 187, 123],
    "right_cheek": [346, 347, 330, 266, 425, 411, 352]
}

def bandpass_filter(signal: np.ndarray, fs: float, low: float = 0.7, high: float = 3.0) -> np.ndarray:
    nyquist = 0.5 * fs
    b, a = butter(3, [low / nyquist, high / nyquist], btype="band")
    return filtfilt(b, a, signal)

def extract_roi_green_mean(frame: np.ndarray, landmarks, indices: list, w: int, h: int) -> float:
    pts = np.array([[int(landmarks[i].x * w), int(landmarks[i].y * h)] for i in indices], np.int32)
    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [pts], 255)
    # Green channel (index 1 in BGR) has maximum hemoglobin absorption
    mean_val = cv2.mean(frame[:, :, 1], mask=mask)[0]
    return float(mean_val)

def analyze_video_rppg(video_path: str, max_frames: int = 180) -> dict:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    mp_face = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=False
    )

    raw_signals = {"forehead": [], "left_cheek": [], "right_cheek": []}
    frame_count = 0

    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = mp_face.process(rgb)

        if results.multi_face_landmarks:
            lms = results.multi_face_landmarks[0].landmark
            for roi_name, idxs in ROI_LANDMARKS.items():
                val = extract_roi_green_mean(frame, lms, idxs, w, h)
                raw_signals[roi_name].append(val)
            frame_count += 1

    cap.release()
    mp_face.close()

    if frame_count < 60:
        raise ValueError("Video must contain at least 2 seconds of a clearly visible face.")

    filtered_signals = {}
    for k, v in raw_signals.items():
        arr = np.array(v, dtype=np.float64)
        # Detrend by normalizing over moving mean
        norm_arr = (arr - np.mean(arr)) / (np.std(arr) + 1e-8)
        filtered_signals[k] = bandpass_filter(norm_arr, fps)

    # 1. Cross-Region Coherence (Pearson correlation across Forehead, L-Cheek, R-Cheek)
    corr_fl = np.corrcoef(filtered_signals["forehead"], filtered_signals["left_cheek"])[0, 1]
    corr_fr = np.corrcoef(filtered_signals["forehead"], filtered_signals["right_cheek"])[0, 1]
    corr_lr = np.corrcoef(filtered_signals["left_cheek"], filtered_signals["right_cheek"])[0, 1]
    mean_coherence = float(np.mean([corr_fl, corr_fr, corr_lr]))

    # 2. Spectral Power & SNR via Welch's method
    combined_pulse = np.mean(
        [filtered_signals["forehead"], filtered_signals["left_cheek"], filtered_signals["right_cheek"]],
        axis=0
    )
    freqs, psd = welch(combined_pulse, fs=fps, nperseg=min(len(combined_pulse), 128))
    valid_mask = (freqs >= 0.7) & (freqs <= 3.0)
    valid_freqs = freqs[valid_mask]
    valid_psd = psd[valid_mask]

    peak_idx = int(np.argmax(valid_psd))
    peak_freq = float(valid_freqs[peak_idx])
    estimated_bpm = round(peak_freq * 60.0, 1)

    # SNR calculation: power near peak (+/- 0.15 Hz) vs remaining spectrum
    signal_band = np.abs(valid_freqs - peak_freq) <= 0.15
    signal_power = np.sum(valid_psd[signal_band])
    noise_power = np.sum(valid_psd[~signal_band]) + 1e-8
    snr_db = float(10.0 * np.log10(signal_power / noise_power))

    # 3. Authenticity Classification Score
    # Real faces exhibit high spatial coherence (>0.55) and positive cardiac SNR
    coherence_score = np.clip((mean_coherence + 0.2) / 1.0, 0.0, 1.0)
    snr_score = np.clip((snr_db + 5.0) / 12.0, 0.0, 1.0)
    authenticity_prob = round(float(0.65 * coherence_score + 0.35 * snr_score), 4)
    is_real = authenticity_prob >= 0.55

    time_axis = [round(i / fps, 3) for i in range(frame_count)]

    return {
        "verdict": "REAL_HUMAN" if is_real else "DEEPFAKE_DETECTED",
        "authenticity_score": authenticity_prob,
        "estimated_bpm": estimated_bpm,
        "spatial_coherence": round(mean_coherence, 3),
        "snr_db": round(snr_db, 2),
        "frames_analyzed": frame_count,
        "time_series": {
            "time_sec": time_axis,
            "forehead": [round(float(x), 4) for x in filtered_signals["forehead"]],
            "left_cheek": [round(float(x), 4) for x in filtered_signals["left_cheek"]],
            "right_cheek": [round(float(x), 4) for x in filtered_signals["right_cheek"]]
        },
        "spectrum": {
            "freqs_hz": [round(float(f), 3) for f in valid_freqs],
            "psd": [round(float(p), 5) for p in valid_psd]
        }
    }
