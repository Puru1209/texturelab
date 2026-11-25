"""Moving-window sum/difference histograms and exact GLCM-equivalent descriptors.

For every local window, a directed pair of pixels (i,j) contributes to
sum s=i+j and difference d=i-j histograms. Contrast and mean are derived
from those histograms. ASM needs the *joint* distribution and cannot in
general be reconstructed exactly from the two marginals; we accumulate
that joint distribution from the same pairs for exact GLCM ASM.
"""
import io
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

DIRECTIONS = {0:(0,1), 45:(-1,1), 90:(-1,0), 135:(-1,-1)}


def decode_image(raw: bytes, filename: str):
    """Return 2D float image, preserving first band of multi-band TIFFs."""
    if filename.lower().endswith(('.tif','.tiff')):
        try:
            import rasterio
            from rasterio.io import MemoryFile
            with MemoryFile(raw) as mem:
                with mem.open() as ds:
                    arr = ds.read(1, masked=True).astype('float64')
                    return np.asarray(arr.filled(np.nan)), ds.profile.copy()
        except Exception:
            pass
    with Image.open(io.BytesIO(raw)) as im:
        if im.mode in ('I;16','I','F'):
            arr = np.asarray(im, dtype=np.float64)
        else:
            arr = np.asarray(im.convert('L'), dtype=np.float64)
    return arr, None


def quantize(arr, levels):
    if arr.ndim != 2: raise ValueError('Image must be 2D')
    finite = np.isfinite(arr)
    if not finite.any(): raise ValueError('Image has no valid pixels')
    lo, hi = np.nanpercentile(arr[finite], [1,99])
    if hi <= lo: lo, hi = np.nanmin(arr[finite]), np.nanmax(arr[finite])
    if hi <= lo: return np.zeros(arr.shape, dtype=np.uint8), finite
    scaled = np.clip((np.nan_to_num(arr, nan=lo)-lo)/(hi-lo),0,1)
    return np.floor(scaled*(levels-1)+1e-9).astype(np.uint16), finite


def local_features(q, valid, window=11, levels=None, angle=0, distance=1):
    """Exact symmetric pair ASM, contrast, mean, without a dense gray-level matrix.

    Original mode uses original grayscale numeric intensities (no quantization).
    Manual mode uses quantized intensities. Both use identical pair statistics.
    """
    if window < 3 or window % 2 == 0:
        raise ValueError('Window must be odd and >= 3')
    if distance < 1 or distance >= window:
        raise ValueError('Distance must be >= 1 and less than window')
    if angle not in DIRECTIONS:
        raise ValueError('Angle must be 0, 45, 90 or 135')
    dy, dx = DIRECTIONS[angle]
    return _local_features_compiled(np.ascontiguousarray(q, dtype=np.float64),
                                    np.ascontiguousarray(valid, dtype=np.bool_),
                                    window, dy * distance, dx * distance)


from numba import njit


@njit(cache=True)
def _local_features_compiled(q, valid, window, dy, dx):
    h, w = q.shape
    radius = window // 2

    result = np.empty((h, w, 3), dtype=np.float32)
    result[:] = np.nan

    max_pairs = window * window

    for y in range(h):
        for x in range(w):

            if not valid[y, x]:
                continue

            y0 = max(0, y - radius)
            y1 = min(h, y + radius + 1)
            x0 = max(0, x - radius)
            x1 = min(w, x + radius + 1)

            # STEP 1: Collect valid pixel pairs
            left = np.empty(max_pairs, dtype=np.float64)
            right = np.empty(max_pairs, dtype=np.float64)
            count = 0

            for py in range(y0, y1):
                by = py + dy

                if by < y0 or by >= y1:
                    continue

                for px in range(x0, x1):
                    bx = px + dx

                    if bx < x0 or bx >= x1:
                        continue

                    if not (valid[py, px] and valid[by, bx]):
                        continue

                    left[count] = q[py, px]
                    right[count] = q[by, bx]
                    count += 1

            if count == 0:
                continue

            # STEP 2: Calculate SUM and DIFFERENCE
            sums = np.empty(count, dtype=np.float64)
            diffs = np.empty(count, dtype=np.float64)

            for p in range(count):
                sums[p] = left[p] + right[p]
                diffs[p] = left[p] - right[p]

            # STEP 3: Construct SUM and DIFFERENCE histograms
            # Each unique value gets its own histogram bin.
            sum_values = np.unique(sums)
            diff_values = np.unique(diffs)

            sum_hist = np.zeros(len(sum_values), dtype=np.float64)
            diff_hist = np.zeros(len(diff_values), dtype=np.float64)

            for p in range(count):
                si = np.searchsorted(sum_values, sums[p])
                di = np.searchsorted(diff_values, diffs[p])

                sum_hist[si] += 1.0
                diff_hist[di] += 1.0

            # Normalize the histograms
            sum_hist /= count
            diff_hist /= count

            # STEP 4: Mean from SUM histogram
            mean = 0.0

            for p in range(len(sum_values)):
                mean += sum_values[p] * sum_hist[p] / 2.0

            # STEP 5: Contrast from DIFFERENCE histogram
            contrast = 0.0

            for p in range(len(diff_values)):
                contrast += (
                    diff_values[p] ** 2
                    * diff_hist[p]
                )

            # STEP 6: Exact symmetric GLCM-equivalent ASM
            # SUM and DIFF marginals alone are insufficient.
            # Use the original joint pixel-pair information.
            matches = 0

            for p in range(count):
                for r in range(count):

                    if (left[p] == left[r]
                            and right[p] == right[r]):
                        matches += 1

                    if (left[p] == right[r]
                            and right[p] == left[r]):
                        matches += 1

            asm = matches / (2.0 * count * count)

            # STEP 7: Store texture features
            result[y, x, 0] = asm
            result[y, x, 1] = contrast
            result[y, x, 2] = mean

    return result





def stretch(arr):
    valid=np.isfinite(arr)
    out=np.zeros(arr.shape,dtype=np.uint8)
    if not valid.any(): return out
    lo,hi=np.percentile(arr[valid],[2,98])
    if hi>lo: out[valid]=np.clip((arr[valid]-lo)/(hi-lo)*255,0,255).astype(np.uint8)
    return out


def png_gray(arr):
    buf=io.BytesIO(); Image.fromarray(stretch(arr)).save(buf,format='PNG'); return buf.getvalue()


def png_labels(labels, n):
    from matplotlib import colormaps
    palette=(colormaps['hsv'](np.arange(n)/max(n, 1))[:,:3]*255).astype(np.uint8)
    rgb=np.zeros((*labels.shape,3),dtype=np.uint8)
    for k in range(n): rgb[labels==k]=palette[k]
    buf=io.BytesIO(); Image.fromarray(rgb).save(buf,format='PNG'); return buf.getvalue()


def cluster_features(features, n_clusters, random_state=42):
    """Fit K-Means for a user-specified K on standardized texture features.

    For practical runtime, fit on at most 30k sampled valid pixels using
    MiniBatchKMeans and assign all valid pixels.
    """
    from sklearn.cluster import MiniBatchKMeans
    if not isinstance(n_clusters, (int, np.integer)) or isinstance(n_clusters, bool) or n_clusters < 2:
        raise ValueError('Number of clusters (K) must be an integer >= 2.')
    if n_clusters > 255:
        raise ValueError('Number of clusters (K) must be <= 255.')
    k = int(n_clusters)
    valid = np.isfinite(features).all(axis=2)
    data = features[valid].astype(np.float32)
    if data.shape[0] < k:
        raise ValueError(f'At least {k} valid pixels are required for K = {k}.')
    scaler = StandardScaler()
    normalized = scaler.fit_transform(data)
    rng = np.random.default_rng(random_state)
    indices = rng.choice(len(normalized), size=min(30_000, len(normalized)), replace=False)
    fit_data = normalized[indices]
    model = MiniBatchKMeans(n_clusters=k, random_state=random_state,
                            batch_size=min(2048, len(fit_data)), n_init=2,
                            max_iter=75)
    model.fit(fit_data)
    labels = np.full(features.shape[:2], 255, dtype=np.uint8)
    label_flat = np.empty(len(normalized), dtype=np.uint8)
    inertia = 0.0
    for start in range(0, len(normalized), 100_000):
        stop = min(start + 100_000, len(normalized))
        batch = normalized[start:stop]
        batch_labels = model.predict(batch).astype(np.uint8)
        label_flat[start:stop] = batch_labels
        inertia += float(np.sum((batch - model.cluster_centers_[batch_labels]) ** 2))
    labels[valid] = label_flat
    metrics = {'inertia': inertia,
               'cluster_counts': np.bincount(label_flat, minlength=k).tolist()}
    return labels, metrics


def cluster_all_k(features, k_min=2, k_max=41, random_state=42):
    """Fit every K on the same standardized texture features; return maps + metrics.

    For practical runtime, fit on at most 30k sampled valid pixels using
    MiniBatchKMeans; assign ALL valid pixels for each K. Models are independent.
    """
    from sklearn.cluster import MiniBatchKMeans
    valid = np.isfinite(features).all(axis=2)
    data = features[valid].astype(np.float32)
    if data.shape[0] < k_max:
        raise ValueError(f'At least {k_max} valid pixels are required to generate all 40 maps.')
    scaler = StandardScaler()
    normalized = scaler.fit_transform(data)
    rng = np.random.default_rng(random_state)
    indices = rng.choice(len(normalized), size=min(30_000, len(normalized)), replace=False)
    fit_data = normalized[indices]
    for k in range(k_min, k_max + 1):
        model = MiniBatchKMeans(n_clusters=k, random_state=random_state,
                                batch_size=min(2048, len(fit_data)), n_init=2,
                                max_iter=75)
        model.fit(fit_data)
        labels = np.full(features.shape[:2], 255, dtype=np.uint8)
        label_flat = np.empty(len(normalized), dtype=np.uint8)
        inertia = 0.0
        for start in range(0, len(normalized), 100_000):
            stop = min(start + 100_000, len(normalized))
            batch = normalized[start:stop]
            batch_labels = model.predict(batch).astype(np.uint8)
            label_flat[start:stop] = batch_labels
            inertia += float(np.sum((batch - model.cluster_centers_[batch_labels]) ** 2))
        labels[valid] = label_flat
        yield k, labels, {'inertia': inertia,
                          'cluster_counts': np.bincount(label_flat, minlength=k).tolist()}
