from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class Box(BaseModel):
    x:int; y:int; w:int; h:int
    label: Literal["ripe","unripe"] = "ripe"
    ripeness: float = 1.0

class FruitDetections(BaseModel):
    count_est:int
    ripe_est:int
    unripe_est:int
    bboxes: List[Box] = []
    method:str

class LeafStains(BaseModel):
    area_pct: float
    clusters: int
    method: str

class ImageInfo(BaseModel):
    path:str; hash:str
    width:int; height:int; timestamp:str

class MissionInfo(BaseModel):
    name:str
    capture_order: Optional[int] = None
    vgps: Optional[dict] = None  # lat/lng/alt cuando lo integres

class QualityInfo(BaseModel):
    sharpness_laplacian: float
    brightness_mean: float
    snr_est: float
    is_usable: bool
    warnings: List[str] = []

class PreprocessInfo(BaseModel):
    denoise: Optional[str] = None
    color_balance: Optional[str] = None
    clahe: bool = True
    scale: float = 1.0

class VegetationIdx(BaseModel):
    exg_mean: float
    vari_mean: float
    cive_mean: float
    leaf_coverage_pct: float

class Artifacts(BaseModel):
    mask_leaves: Optional[str] = None
    mask_fruits: Optional[str] = None
    thumb: Optional[str] = None

class ModelInfo(BaseModel):
    fruit_detector: dict
    leaf_classifier: dict

class FrameRecord(BaseModel):
    image: ImageInfo
    mission: MissionInfo
    quality: QualityInfo
    preprocess: PreprocessInfo
    vegetation_indices: VegetationIdx
    detections: dict
    artifacts: Artifacts
    model: ModelInfo
    runtime_ms: int
    version: str = "analysis_schema_v1"
