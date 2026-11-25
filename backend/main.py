import io, json, zipfile
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
import numpy as np
from .algorithms import decode_image,quantize,local_features,cluster_features,png_gray,png_labels

ALLOWED_WINDOWS = (11, 13, 15, 17, 19)

app=FastAPI(title='TextureLab API',version='1.0.0')

@app.get('/health')
def health(): return {'status':'ok'}

@app.post('/analyze')
async def analyze(file:UploadFile=File(...), window:int=Form(11), levels:int=Form(32),
                  angle:int=Form(0), distance:int=Form(1),
                  k:int=Form(...), gray_mode:str=Form("manual")):
    try:
        if window not in ALLOWED_WINDOWS:
            raise ValueError('Moving window size must be an odd size from 11 to 19 (11, 13, 15, 17, or 19)')
        if k < 2 or k > 255:
            raise ValueError('Number of clusters (K) must be an integer between 2 and 255')
        if gray_mode not in ('original', 'manual'): raise ValueError('Invalid gray-level processing mode')
        if gray_mode == 'manual' and levels not in (8,16,32,64,256):
            raise ValueError('Gray levels must be 8, 16, 32, 64 or 256')
        raw=await file.read()
        if len(raw)>250_000_000: raise ValueError('Upload exceeds 250 MB; use a smaller file or a tiled workflow')
        arr,profile=decode_image(raw,file.filename or 'image.png')
        if arr.size > 16_000_000:
            raise ValueError('This local setup supports up to 16 million pixels per run for memory safety. Larger images need tiled processing.')
        if gray_mode == 'original':
            valid = np.isfinite(arr)
            if not valid.any(): raise ValueError('Image has no valid pixels')
            q = arr.copy()
        else:
            q,valid=quantize(arr,levels)
        features=local_features(q,valid,window,levels,angle,distance)
        labels, metrics = cluster_features(features, k)
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('input.png',png_gray(arr))
            for i,name in enumerate(('asm','contrast','mean')):
                z.writestr(f'{name}.png',png_gray(features[:,:,i]))
            cluster_png = png_labels(labels, k)
            z.writestr(f'clusters/k_{k:02d}.png', cluster_png)
            z.writestr('clusters.png', cluster_png)
            if profile:
                try:
                    import rasterio
                    from rasterio.io import MemoryFile
                    tifprofile=profile.copy()
                    tifprofile.update(count=1,dtype='uint8',nodata=255,compress='lzw')
                    with MemoryFile() as mem:
                        with mem.open(**tifprofile) as dst: dst.write(labels,1)
                        tif_bytes = mem.read()
                        z.writestr(f'clusters/k_{k:02d}.tif', tif_bytes)
                        z.writestr('clusters_georeferenced.tif', tif_bytes)
                except Exception: pass
            buffer=io.BytesIO();np.savez_compressed(buffer,asm=features[:,:,0],contrast=features[:,:,1],mean=features[:,:,2],labels=labels,processed_intensities=q)
            z.writestr('numerical_results.npz',buffer.getvalue())
            metadata={'parameters':dict(window=window,levels=(None if gray_mode == 'original' else levels),gray_mode=gray_mode,angle=angle,distance=distance,k=k),
                      'shape':list(arr.shape),'metrics':metrics,'metrics_by_k':{str(k):metrics},
                      'method':'SUM-DIFF histograms for contrast and mean; exact symmetric local GLCM ASM from same pairs',
                      'nodata_label':255}
            z.writestr('metadata.json',json.dumps(metadata,indent=2))
        out.seek(0)
        return StreamingResponse(out,media_type='application/zip',headers={'Content-Disposition':'attachment; filename="texture_results.zip"'})
    except (ValueError,TypeError) as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc
