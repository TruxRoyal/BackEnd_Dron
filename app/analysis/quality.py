# app/analysis/quality.py
import cv2
import numpy as np

def assess_quality(img_bgr, cfg):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    sharp = float(lap.var())

    mean_brightness = float(gray.mean())

    # estimación muy simple de SNR
    noise = gray.astype(np.float32) - cv2.GaussianBlur(gray, (5,5), 0)
    snr = float(np.mean(gray) / (np.std(noise) + 1e-6))

    warn = []
    if sharp < getattr(cfg, "LAPLACIAN_MIN", 80.0):
        warn.append("posible desenfoque")
    if mean_brightness < getattr(cfg, "BRIGHTNESS_MIN", 25.0):
        warn.append("subexpuesta")
    if mean_brightness > getattr(cfg, "BRIGHTNESS_MAX", 230.0):
        warn.append("sobreexpuesta")

    usable = len(warn) == 0 or not getattr(cfg, "FAIL_ON_POOR_QUALITY", False)

    return {
        "sharpness_laplacian": sharp,
        "brightness_mean": mean_brightness,
        "snr_est": snr,
        "is_usable": bool(usable),
        "warnings": warn
    }
