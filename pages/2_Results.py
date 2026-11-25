"""Compact TextureLab results page: original saved backend outputs."""
import html
import io
import json
import sys
import zipfile
from pathlib import Path
from urllib.parse import quote

import streamlit as st

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent))
sys.path.insert(0, str(here.parent / "frontend"))

try:
    from run_store import list_runs, load_run
except ImportError:
    from frontend.run_store import list_runs, load_run

st.set_page_config(page_title="TextureLab | Results", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.stApp {background:#f5f7fb;color:#17243b;}
section[data-testid="stSidebar"] {background:#fff;}
[data-testid="stMainBlockContainer"] {max-width:100%;padding:1.4rem 2.4rem 3rem;}
[data-testid="stMain"] h1 {font-size:2rem;font-weight:800;margin-bottom:.6rem;}
[data-testid="stMain"] h2 {font-size:1.45rem;font-weight:750;margin:1rem 0 .5rem;}
[data-testid="stMain"] h3 {font-size:1.05rem;font-weight:700;margin:.4rem 0;}
[data-testid="stMain"] [data-testid="stImage"] {border-radius:8px;overflow:hidden;}
[data-testid="stMain"] [data-testid="stImageCaption"] {font-size:.78rem;}
[data-testid="stMain"] [data-testid="stVerticalBlock"] {gap:.55rem;}
@media(max-width:800px){[data-testid="stMainBlockContainer"]{padding:1rem;}}
</style>
""", unsafe_allow_html=True)

st.title("TextureLab | Results")
if st.button("← Back to Analysis"):
    try:
        st.switch_page("streamlit_app.py")
    except Exception:
        try:
            st.switch_page("app.py")
        except Exception:
            st.switch_page("frontend/app.py")

runs = list_runs()
if not runs:
    st.info("No saved analyses yet. Run an analysis first.")
    st.stop()

run_ids = [run["id"] for run in runs]
chosen = st.query_params.get("run")
if chosen not in run_ids:
    chosen = st.session_state.get("active_run_id")
if chosen not in run_ids:
    chosen = run_ids[0]
st.session_state["active_run_id"] = chosen
if st.query_params.get("run") != chosen:
    st.query_params["run"] = chosen

with st.sidebar:
    st.subheader("Saved Analyses")
    for number, item in enumerate(sorted(runs, key=lambda x: x["id"]), 1):
        rid = item["id"]
        label = f"Run {number} · {item.get('filename', 'Image')}"
        if rid == chosen:
            st.markdown(f"**{html.escape(label)}**")
        else:
            st.markdown(f'<a href="/Results?run={quote(rid)}" target="_blank" rel="noopener noreferrer">{html.escape(label)}</a>', unsafe_allow_html=True)

with st.expander(f"Saved Results ({len(runs)}) — open another run in a new tab", expanded=False):
    for number, item in enumerate(sorted(runs, key=lambda x: x["id"]), 1):
        rid = item["id"]
        st.markdown(f'<a href="/Results?run={quote(rid)}" target="_blank" rel="noopener noreferrer">Run {number} · {html.escape(item.get("filename", "Image"))}</a>', unsafe_allow_html=True)

try:
    run_info, blob, preview = load_run(chosen)
    archive = zipfile.ZipFile(io.BytesIO(blob))
    metadata = json.loads(archive.read("metadata.json"))
except (OSError, ValueError, KeyError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
    st.error(f"Could not open this saved result: {exc}")
    st.stop()

params = run_info.get("parameters", {})
meta_params = metadata.get("parameters", {})
k_display = params.get("k", meta_params.get("k", params.get("k_range", "2–41")))
gray_mode_val = params.get("gray_mode", meta_params.get("gray_mode"))
gray_display = "Original" if gray_mode_val == "original" else params.get("levels", meta_params.get("levels", "?"))
st.caption(f"{run_info.get('filename','Image')}  |  Window: {params.get('window','?')} × {params.get('window','?')}  |  "
           f"Gray levels: {gray_display}  |  Direction: {params.get('angle','?')}°  |  "
           f"Pixel distance: {params.get('distance','?')}  |  K: {k_display}")

with archive as z:
    if preview:
        st.subheader("Input Image")
        st.image(preview, width=300)

    st.subheader("Texture Feature Maps")
    feature_cols = st.columns(3, gap="medium")
    for col, name, file in zip(feature_cols, ["ASM", "Contrast", "Mean"], ["asm.png", "contrast.png", "mean.png"]):
        with col:
            st.markdown(f"**{name}**")
            st.image(z.read(file), use_container_width=True)

    metrics_by_k = metadata.get("metrics_by_k", {})
    available_ks = sorted(int(k_str) for k_str in metrics_by_k.keys() if k_str.isdigit())
    if not available_ks and "k" in meta_params:
        available_ks = [int(meta_params["k"])]

    if len(available_ks) == 1:
        k = available_ks[0]
        st.subheader(f"K-Means Clustering | K = {k}")
        cluster_path = f"clusters/k_{k:02d}.png"
        img_bytes = z.read(cluster_path) if cluster_path in z.namelist() else z.read("clusters.png")
        st.image(img_bytes, caption=f"K-Means Cluster Map (K = {k})", width=520)
        metrics = metrics_by_k.get(str(k), metadata.get("metrics", {}))
        if "inertia" in metrics:
            st.caption(f"Inertia: {metrics['inertia']:,.1f}")
    else:
        k_list = available_ks if available_ks else list(range(2, 42))
        st.subheader(f"K-Means Clustering | K = {min(k_list)}–{max(k_list)}")
        for row_start in range(0, len(k_list), 4):
            cols = st.columns(4, gap="small")
            for col, k in zip(cols, k_list[row_start:row_start + 4]):
                with col:
                    st.markdown(f"**K = {k}**")
                    st.image(z.read(f"clusters/k_{k:02d}.png"), use_container_width=True)
                    metrics = metrics_by_k.get(str(k), {})
                    if "inertia" in metrics:
                        st.caption(f"Inertia: {metrics['inertia']:,.1f}")

    st.download_button("Download Results ZIP", data=blob,
                       file_name=f"texture_results_{chosen}.zip", mime="application/zip")
