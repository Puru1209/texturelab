"""SUM-DIFF texture analysis — satellite-imaging themed Streamlit frontend.

The FastAPI processing endpoint and its parameters are unchanged.
"""
import io
import html
import os
import subprocess
import time
from urllib.parse import quote

import numpy as np
import requests
import streamlit as st
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image

def _ensure_backend_running(port=8000):
    try:
        r = requests.get(f"http://127.0.0.1:{port}/health", timeout=1)
        if r.status_code == 200:
            return
    except Exception:
        pass
    try:
        project_root = Path(__file__).resolve().parents[1]
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=str(project_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        for _ in range(12):
            time.sleep(0.5)
            try:
                r = requests.get(f"http://127.0.0.1:{port}/health", timeout=1)
                if r.status_code == 200:
                    break
            except Exception:
                pass
    except Exception:
        pass

_ensure_backend_running()

st.set_page_config(
    page_title="SUM-DIFF | Analysis", page_icon="◈",
    layout="wide", initial_sidebar_state="expanded"
)

st.markdown("""
<style>
:root { color-scheme: light; }
.stApp {
    background-color: #f5f7fb;
    background-image:
        linear-gradient(rgba(99,102,241,.035) 1px,transparent 1px),
        linear-gradient(90deg,rgba(99,102,241,.035) 1px,transparent 1px),
        radial-gradient(ellipse at 90% 5%,rgba(99,102,241,.08),transparent 46%);
    background-size: 36px 36px,36px 36px,auto;
    color: #17243b;
}
section[data-testid="stSidebar"] {
    width: 33.333vw !important;
    min-width: 33.333vw !important;
    max-width: 33.333vw !important;
    background: #ffffff !important;
    border-right: 1px solid #d9e2ee;
}
section[data-testid="stSidebar"] > div { width: 100% !important; }
section[data-testid="stMain"] .block-container {
    width: 100% !important; max-width: 100% !important;
    padding: 2rem 2.3rem 4rem !important;
}
[data-testid="stMain"] h2 { font-size: 30px !important; }
[data-testid="stMain"] h3 { font-size: 26px !important; }
[data-testid="stMain"] p, [data-testid="stMain"] li {
    font-size: 19px !important; line-height: 1.65 !important;
}
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { font-size: 30px !important; font-weight: 800 !important; }
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] label p {
    font-size: 22px !important; font-weight: 650 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] div,
[data-testid="stSidebar"] [data-baseweb="select"] span {
    font-size: 21px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div { min-height: 48px !important; }
[data-testid="stSidebar"] [data-testid="stSlider"] p,
[data-testid="stSidebar"] [data-testid="stSlider"] span { font-size: 20px !important; }
[data-testid="stSidebar"] input { font-size: 20px !important; min-height: 46px !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    font-size: 17px !important; line-height: 1.6 !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 1.1rem !important; }
[data-testid="stSidebar"] [data-testid="stSlider"] [role="slider"] {
    background-color: #6366f1 !important;
}
.hero {
    background: linear-gradient(115deg,#e7ecff,#f1f4ff 70%,#e8f6f4);
    border: 1px solid #d5dff2; border-radius: 17px;
    padding: 38px 42px; margin-bottom: 30px;
    box-shadow: 0 14px 35px rgba(0,0,0,.15);
}
.hero-kicker { color: #4f46e5; font-size: 15px; font-weight: 800; letter-spacing: 2px; }
.hero-title { color: #17243b; font-size: 40px; font-weight: 800; margin: 16px 0; line-height: 1.2; }
.hero-subtitle { color: #42516a; font-size: 19px; line-height: 1.5; }
.step { color: #4f46e5; font-size: 16px; font-weight: 800; letter-spacing: 1.5px; margin: 24px 0 12px; }
.explain { font-size: 20px; line-height: 1.7; color: #475569; margin: 10px 0 20px; }
[data-testid="stMain"] [data-testid="stFileUploader"] button,
[data-testid="stMain"] [data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
    font-size: 21px !important; font-weight: 700 !important;
    min-height: 56px !important; padding: 12px 28px !important;
    border: 2px solid #818cf8 !important; border-radius: 10px !important;
    background: #eef2ff !important; color: #312e81 !important;
}
[data-testid="stMain"] [data-testid="stFileUploader"] button:hover { background: #e0e7ff !important; }
[data-testid="stMain"] div.stButton > button[kind="primary"] {
    background: #4f46e5 !important; color: white !important;
    border: 1px solid #a5b4fc !important; border-radius: 12px !important;
    font-size: 22px !important; font-weight: 750 !important;
    min-height: 60px !important; padding: 14px 30px !important;
}
[data-testid="stMain"] div.stButton > button[kind="primary"]:hover { background: #4338ca !important; }
[data-testid="stMain"] [data-testid="stImageCaption"] { font-size: 17px !important; }
[data-testid="stMain"] [data-testid="stAlert"] p { font-size: 18px !important; }
@media (max-width: 900px) {
    section[data-testid="stSidebar"] { width: 85vw !important; min-width: 85vw !important; max-width: 85vw !important; }
    .hero { padding: 25px !important; }
    .hero-title { font-size: 30px !important; }
}

/* Accessible light palette and tidy layout */
.stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #24324a !important; }
.hero { box-shadow: 0 10px 30px rgba(53,65,110,.08); }
.hero-title { color: #17243b !important; }
.hero-subtitle, .explain { color: #475569 !important; }
.hero-kicker, .step { color: #4f46e5 !important; }
[data-testid="stSidebar"] { background: #fff !important; }
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { color: #24324a !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #64748b !important; }
[data-testid="stSidebar"] [data-testid="stAlert"] p { color: #1e3a8a !important; }
[data-testid="stSidebar"] [data-baseweb="select"] * { color: #24324a !important; }
[data-testid="stMain"] [data-testid="stImage"] { border-radius: 12px; overflow: hidden; }
[data-testid="stMain"] div.stButton > button[kind="primary"] { color: #fff !important; }
[data-testid="stMain"] [data-testid="stFileUploader"] button { color: #312e81 !important; }
[data-testid="stMain"] [data-testid="stFileUploader"] { border-radius: 14px; }
[data-testid="stMain"] [data-testid="stAlert"] p { color: #24324a !important; }
</style>
""", unsafe_allow_html=True)

# HTML begins at column zero to avoid Markdown interpreting it as a code block.
st.markdown("""
<div class="hero">
<div class="hero-kicker">DIGITAL IMAGE PROCESSING · TEXTURE INTELLIGENCE</div>
<div class="hero-title">SUM-DIFF Texture Analysis</div>
<div class="hero-subtitle">Moving-window texture features · ASM / Contrast / Mean · K-Means clustering</div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Analysis Controls")
    st.caption("Configure the moving-window texture analysis and K-Means clustering parameters.")
    st.divider()
    window = st.selectbox("Moving Window Size", [11, 13, 15, 17, 19], index=0,
                          format_func=lambda value: f"{value} × {value}",
                          help="Odd local neighborhood size (11×11 to 19×19) used to calculate texture.")
    gray_mode = st.radio("Gray-Level Processing", ["Original Image (No Quantization)", "Manual Quantization"], index=0)
    use_original = gray_mode.startswith("Original")
    levels = None
    if not use_original:
        levels = st.selectbox("Gray Levels", [8, 16, 32, 64, 256], index=2)
    angle = st.selectbox("Direction", [0, 45, 90, 135],
                         format_func=lambda value: f"{value}°",
                         help="Direction between neighboring pixels.")
    distance = st.slider("Pixel Distance", 1, window - 1, 1,
                         help="Distance between neighboring pixels.")
    st.info("K-Means cluster count (K) is requested from you at runtime each time you run an analysis.")
    st.divider()
    api_url = st.text_input("FastAPI Server", os.getenv("API_URL", "http://127.0.0.1:8000"))
    st.caption("Backend: `python -m uvicorn backend.main:app --reload`")

st.markdown('<div class="step">01 / IMAGE INPUT</div>', unsafe_allow_html=True)
st.subheader("Upload Your Image")
st.markdown("""
<div class="explain">Select a PNG, JPEG or TIFF image. The algorithm examines local gray-level
relationships within a moving window to generate ASM, Contrast and Mean texture features.</div>
""", unsafe_allow_html=True)

uploaded = st.file_uploader("Choose an Image", type=["png", "jpg", "jpeg", "tif", "tiff"])
if uploaded is None:
    st.info("Upload an image to begin the analysis.")
    st.stop()

raw = uploaded.getvalue()
try:
    preview = None
    if uploaded.name.lower().endswith((".tif", ".tiff")):
        try:
            from rasterio.io import MemoryFile
            with MemoryFile(raw) as memory:
                with memory.open() as dataset:
                    data = dataset.read(1, masked=True).filled(np.nan).astype(float)
            finite = data[np.isfinite(data)]
            if finite.size > 0:
                lo, hi = np.percentile(finite, [2, 98])
                preview = np.uint8(np.clip(
                    (np.nan_to_num(data, nan=lo) - lo) / max(hi - lo, 1e-12) * 255,
                    0, 255
                ))
        except Exception:
            pass
    if preview is None:
        preview = Image.open(io.BytesIO(raw)).convert("RGB")

    image_col, detail_col = st.columns([1, 1.5], gap="large", vertical_alignment="center")
    with image_col:
        st.image(preview, caption="Uploaded input image", width=420)
    with detail_col:
        st.markdown("### Ready to Analyze")
        st.markdown(f"**Filename:** {uploaded.name}")
        st.markdown(f"**Window Size:** {window} × {window}")
        st.markdown(f"**Direction:** {angle}°")
        st.markdown(f"**Pixel Distance:** {distance}")
        st.markdown(f"**Gray-Level Processing:** {'Original (No Quantization)' if use_original else str(levels) + ' levels'}")
        st.markdown("**K-Means Clusters (K):** Entered at runtime during execution")
        st.markdown("""
<div class="explain">The FastAPI backend calculates the original texture maps and
performs K-Means clustering. This interface does not recolor or recalculate its outputs.</div>
""", unsafe_allow_html=True)
except Exception as exc:
    st.error(f"Could not preview image: {exc}")
    st.stop()


@st.dialog("Enter K Value for K-Means Clustering")
def prompt_k_dialog():
    st.markdown("Specify the number of clusters (**K**) to use for K-Means clustering during this execution.")
    k_val = st.number_input(
        "Number of Clusters (K)",
        min_value=2,
        max_value=255,
        value=None,
        step=1,
        placeholder="Enter an integer K (e.g., 4)",
        key=f"runtime_k_input_{st.session_state.get('k_prompt_seq', 0)}",
    )
    confirm_col, cancel_col = st.columns(2)
    with confirm_col:
        if st.button("Confirm & Run Analysis", type="primary", use_container_width=True):
            if k_val is None:
                st.warning("Please enter a valid K value (integer >= 2).")
            else:
                st.session_state["pending_run_k"] = int(k_val)
                st.rerun()
    with cancel_col:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


if st.button("Run Texture Analysis", type="primary", use_container_width=True):
    st.session_state["k_prompt_seq"] = st.session_state.get("k_prompt_seq", 0) + 1
    prompt_k_dialog()

if "pending_run_k" in st.session_state:
    chosen_k = st.session_state.pop("pending_run_k")
    with st.spinner(f"Calculating texture features and K-Means clustering (K = {chosen_k})…"):
        try:
            payload = {
                "window": window,
                "angle": angle,
                "distance": distance,
                "k": chosen_k,
                "gray_mode": "original" if use_original else "manual",
            }
            if not use_original:
                payload["levels"] = levels
            response = requests.post(
                api_url.rstrip("/") + "/analyze",
                files={"file": (uploaded.name, raw, "application/octet-stream")},
                data=payload,
                timeout=3600,
            )
            if not response.ok:
                try:
                    message = response.json().get("detail", response.text)
                except ValueError:
                    message = response.text
                st.error(f"Analysis failed: {message}")
            else:
                preview_buffer = io.BytesIO()
                if isinstance(preview, np.ndarray):
                    Image.fromarray(preview).convert("RGB").save(preview_buffer, format="PNG")
                else:
                    preview.save(preview_buffer, format="PNG")
                st.session_state["result_zip"] = response.content
                st.session_state["input_filename"] = uploaded.name
                st.session_state["input_preview_png"] = preview_buffer.getvalue()
                from run_store import save_run
                run_id = save_run(response.content, preview_buffer.getvalue(), uploaded.name,
                                  {"window": window, "levels": levels,
                                   "gray_mode": "original" if use_original else "manual",
                                   "angle": angle, "distance": distance, "k": chosen_k})
                st.session_state["active_run_id"] = run_id
                st.success(f"Analysis complete (K = {chosen_k})! A new, permanent Results page has been saved. Previous runs remain unchanged.")
        except requests.RequestException as exc:
            st.error(f"Cannot connect to FastAPI: {exc}")

if "active_run_id" in st.session_state:
    rid = st.session_state["active_run_id"]
    st.success("Your latest run is saved. Open it in a new browser tab to keep the Analysis page available.")
    st.markdown(f'<a href="/Results?run={quote(rid)}" target="_blank" rel="noopener noreferrer">Open latest Results page in a new tab ↗</a>', unsafe_allow_html=True)
    if st.button("View Latest Results in This Tab", type="primary", use_container_width=True):
        st.query_params["run"] = rid
        st.switch_page("pages/2_Results.py")

st.divider()
st.subheader("All Saved Analysis Pages")
from run_store import list_runs
saved_runs = list_runs()
if saved_runs:
    st.caption(f"{len(saved_runs)} saved analysis run(s). Each link opens a separate Results tab.")
    for number, item in enumerate(sorted(saved_runs, key=lambda r: r["id"]), start=1):
        rid = item["id"]
        p = item.get("parameters", {})
        k_label = p.get("k", p.get("k_range", "?"))
        label = f"Run {number}: {item.get('filename','Image')} — Window {p.get('window','?')} · Gray {('Original' if p.get('gray_mode') == 'original' else p.get('levels','?'))} · {p.get('angle','?')}° · Distance {p.get('distance','?')} · K {k_label}"
        st.markdown(f'<a href="/Results?run={quote(rid)}" target="_blank" rel="noopener noreferrer">{html.escape(label)} ↗</a>', unsafe_allow_html=True)
else:
    st.caption("Your completed analyses will appear here automatically.")
