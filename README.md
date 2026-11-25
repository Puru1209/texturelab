---
title: TextureLab - SUM-DIFF Texture Analysis
emoji: ◈
colorFrom: indigo
colorTo: blue
sdk: streamlit
sdk_version: 1.35.0
app_file: frontend/app.py
pinned: false
---

# TextureLab — SUM-DIFF Texture Analysis and K-Means

A runnable Streamlit frontend + FastAPI backend for coursework texture analysis.

## Windows setup (PowerShell, from the project directory)

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If activation is blocked by execution policy, use `.venv\Scripts\python.exe` instead of `python` and `.venv\Scripts\streamlit.exe` instead of `streamlit`.

**Terminal 1 — backend**
```powershell
python -m uvicorn backend.main:app --reload
```
API docs: http://127.0.0.1:8000/docs

**Terminal 2 — frontend**
```powershell
streamlit run frontend/app.py
```
Frontend: http://localhost:8501

## How to use
1. Upload PNG/JPEG/TIFF (for multiband TIFF the first band is selected).
2. Choose odd moving window, gray levels, offset direction, distance, and cluster count.
3. Click **Run texture analysis**.
4. Review three texture maps and clustered map, download the results ZIP.

## Mathematics
For local neighbor pairs (i,j), sum S=i+j and difference D=i-j.
Let normalized histograms be P_S and P_D.
- Contrast = Σ_d d² P_D(d)
- Mean = ½ Σ_s s P_S(s)
- ASM = Σ_i Σ_j P(i,j)², where P(i,j) is the **symmetric normalized local co-occurrence matrix**.

**Important methodological distinction:** exact ASM is not recoverable from sum/difference *marginals alone*. We calculate exact ASM from the same local pixel pairs, while contrast and mean are calculated using sum/difference histograms. This yields features equivalent to a symmetric GLCM. Do not describe ASM as being computed exclusively from the two marginals.

Images are 1st/99th-percentile quantized. At edges, the intensity array is edge-padded but validity is false outside image, so only actual pixel pairs contribute. TIFF nodata is masked. Output `.npz` contains raw values; PNGs are individually contrast-stretched for visualization. TIFF input additionally exports a georeferenced label TIFF when possible. K-Means uses z-score normalized feature vectors and deterministic seed 42.

## Files in ZIP
- input.png, asm.png, contrast.png, mean.png, clusters.png
- numerical_results.npz (raw features, labels, quantized input)
- metadata.json (parameters, inertia, cluster sizes)
- clusters_georeferenced.tif (when source is readable GeoTIFF)

## Validation
```powershell
pip install pytest
python -m pytest -q
```
`tests/test_algorithms.py` compares center pixel values against scikit-image GLCM.

## Limitations / extensions
- 512 × 512 max for CPU processing. A Python per-pixel loop favors clarity over speed.
- Cluster IDs are arbitrary and do not imply semantic land-cover classes.
- The tool currently supports one direction/distance per run, not averaged directional textures.
- The app does not implement a marginal-only approximate ASM estimator. For strict SUM-DIFF-only ASM coursework, ask the instructor for the prescribed approximation/formula.
