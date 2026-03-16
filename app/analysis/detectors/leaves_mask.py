# app/analysis/detectors/leaves_mask.py
import cv2
import numpy as np

def segment_leaves(img_bgr, idx, exg_thresh=None):
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    lower = np.array([25,  25,  25], dtype=np.uint8)
    upper = np.array([95, 255, 255], dtype=np.uint8)
    mask_hsv = cv2.inRange(hsv, lower, upper)

    if exg_thresh is not None:
        G = img_bgr[:,:,1].astype(np.float32)
        R = img_bgr[:,:,2].astype(np.float32)
        B = img_bgr[:,:,0].astype(np.float32)
        exg = 2*G - R - B
        exg = (exg - exg.min())/(exg.max()-exg.min()+1e-6)
        mask_exg = (exg > float(exg_thresh)).astype(np.uint8)*255
        mask = cv2.bitwise_and(mask_hsv, mask_exg)
    else:
        mask = mask_hsv

    k = np.ones((5,5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)
    return mask
