# app/analysis/indices.py
import numpy as np
import cv2

def compute_indices(img_bgr):
    img = img_bgr.astype(np.float32) / 255.0
    B, G, R = img[:,:,0], img[:,:,1], img[:,:,2]
    exg  = 2*G - R - B
    vari = (G - R) / np.clip((G + R - B), 1e-6, None)
    cive = 0.441*R - 0.811*G + 0.385*B + 18.78745
    return {
        "exg_mean": float(np.nanmean(exg)),
        "vari_mean": float(np.nanmean(vari)),
        "cive_mean": float(np.nanmean(cive))
    }

def leaf_coverage(mask):
    if mask.size == 0:
        return 0.0
    return 100.0 * (mask > 0).mean()
