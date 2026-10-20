import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="SafeGuard: rPPG Deepfake Detector", layout="wide")
st.title("SafeGuard: Biological Heartbeat Deepfake Detection")

api_url = st.sidebar.text_input("Backend API Endpoint", value="http://localhost:8000/analyze")

uploaded_file = st.file_uploader("Upload a 5-10 second face video (.mp4)", type=["mp4", "mov", "webm"])

if uploaded_file and st.button("Extract Biological Pulse & Verify"):
    col_vid, col_res = st.columns([1, 2])
    with col_vid:
        st.video(uploaded_file)

    with st.spinner("Tracking facial ROIs and filtering green-channel rPPG signals..."):
        try:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "video/mp4")}
            resp = requests.post(api_url, files=files, timeout=60)
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to connect to backend at {api_url}: {e}")
            st.stop()

    if resp.status_code == 200:
        data = resp.json()
        with col_res:
            if data["verdict"] == "REAL_HUMAN":
                st.success(f"VERDICT: AUTHENTIC HUMAN PULSE ({data['authenticity_score']*100:.1f}% Confidence)")
            else:
                st.error(f"VERDICT: SYNTHETIC DEEPFAKE DETECTED ({(1-data['authenticity_score'])*100:.1f}% Confidence)")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Estimated Heart Rate", f"{data['estimated_bpm']} BPM")
            m2.metric("Spatial Coherence", f"{data['spatial_coherence']}")
            m3.metric("Cardiac SNR", f"{data['snr_db']} dB")
            m4.metric("Frames Analyzed", data["frames_analyzed"])

            st.subheader("Bandpass-Filtered rPPG Waveforms (Forehead vs. Cheeks)")
            ts_df = pd.DataFrame(data["time_series"]).set_index("time_sec")
            st.line_chart(ts_df)

            st.subheader("Cardiac Frequency Power Spectrum (0.7 Hz - 3.0 Hz)")
            spec_df = pd.DataFrame(data["spectrum"]).set_index("freqs_hz")
            st.area_chart(spec_df)
    else:
        st.error(f"Error ({resp.status_code}): {resp.text}")