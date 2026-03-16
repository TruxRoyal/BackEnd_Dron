# app/tools/analysis_charts.py
from __future__ import annotations
import argparse, os, math
from pathlib import Path
from typing import Any, Dict, List, Optional

from pymongo import MongoClient
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

DB_NAME = os.getenv("MONGO_DB", "drone_analysis")
COLL_FRAMES = os.getenv("MONGO_FRAMES_COLL", "frames")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

# --------- Util --------------------------------------------------------------
def _iso_to_ts(s: Optional[str]) -> Optional[pd.Timestamp]:
    if not s:
        return None
    if len(s) >= 5 and s[-5] in ['+','-'] and s[-3] != ':':
        s = s[:-2] + ':' + s[-2:]
    try:
        return pd.to_datetime(s, utc=True)
    except Exception:
        return None

def _same_day_or_identical_ts(ts_series: pd.Series) -> bool:
    s = ts_series.dropna()
    if s.empty:
        return True
    same_instant = s.nunique() == 1
    same_day = s.dt.date.nunique() == 1
    return same_instant or same_day

# --------- Carga de datos ----------------------------------------------------
def fetch_frames(mission: str,
                 date_from: Optional[str],
                 date_to: Optional[str],
                 limit: Optional[int]) -> pd.DataFrame:
    cli = MongoClient(MONGO_URI)
    coll = cli[DB_NAME][COLL_FRAMES]

    q: Dict[str, Any] = {"mission.name": mission}
    if date_from or date_to:
        rng: Dict[str, Any] = {}
        if date_from:
            rng["$gte"] = date_from
        if date_to:
            rng["$lte"] = date_to
        q["image.timestamp"] = rng

    proj = {
        "_id": 1,
        "filename": 1,
        "image.timestamp": 1,
        "image.width": 1,
        "image.height": 1,
        "vegetation_indices.leaf_coverage_pct": 1,
        "vegetation_indices.exg_mean": 1,
        "vegetation_indices.vari_mean": 1,
        "vegetation_indices.cive_mean": 1,
        "quality.sharpness_laplacian": 1,
        "detections.fruits.count_est": 1,
        "detections.fruits.ripe_est": 1,
        "detections.fruits.unripe_est": 1,
        "detections.leaf_stains.area_pct": 1,
        "detections.leaf_stains.method": 1,
        "detections.fruit_detection.malformed": 1,
    }

    cursor = coll.find(q, proj).sort([("image.timestamp", 1), ("filename", 1)])
    if limit:
        cursor = cursor.limit(int(limit))

    rows: List[Dict[str, Any]] = []
    for doc in cursor:
        vi = doc.get("vegetation_indices", {}) or {}
        ql = doc.get("quality", {}) or {}
        det = doc.get("detections", {}) or {}
        fr = det.get("fruits", {}) or {}
        ls = det.get("leaf_stains", {}) or {}
        fx = det.get("fruit_detection", {}) or {}
        img = doc.get("image", {}) or {}
        ts_iso = img.get("timestamp")

        rows.append({
            "frame_id": doc.get("_id"),
            "filename": doc.get("filename"),
            "ts_iso": ts_iso,
            "ts": _iso_to_ts(ts_iso),
            "width": img.get("width"),
            "height": img.get("height"),
            "leaf_coverage_pct": vi.get("leaf_coverage_pct"),
            "exg_mean": vi.get("exg_mean"),
            "vari_mean": vi.get("vari_mean"),
            "cive_mean": vi.get("cive_mean"),
            "sharpness_laplacian": ql.get("sharpness_laplacian"),
            "fruit_count": fr.get("count_est"),
            "ripe": fr.get("ripe_est"),
            "unripe": fr.get("unripe_est"),
            "stains_area_pct": ls.get("area_pct"),
            "stains_method": ls.get("method"),
            "malformed": fx.get("malformed"),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Orden estable: por ts si existe, si no por filename
    if df["ts"].notna().any():
        df = df.sort_values(["ts", "filename"], kind="stable")
    else:
        df = df.sort_values(["filename"], kind="stable")

    df.reset_index(drop=True, inplace=True)
    df["frame_idx"] = np.arange(1, len(df) + 1)

    # --- Derivadas útiles (sin evaluar Series como booleano) ---
    n = len(df)
    def _series_or_zeros(col: str) -> pd.Series:
        if col in df:
            return df[col].fillna(0)
        # si no existe la columna, devolvemos una serie de ceros del mismo largo
        return pd.Series(np.zeros(n, dtype=float), index=df.index)

    total = _series_or_zeros("fruit_count")
    ripe  = _series_or_zeros("ripe")

    with np.errstate(divide='ignore', invalid='ignore'):
        df["ripe_pct"] = np.where(total > 0, (ripe / total) * 100.0, np.nan)


    return df

# --------- Helpers de guardado ----------------------------------------------
def ensure_out(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

def save_csv(df: pd.DataFrame, out_dir: Path, name: str) -> Path:
    p = out_dir / f"{name}.csv"
    df.to_csv(p, index=False)
    return p

def save_summary(df: pd.DataFrame, out_dir: Path, mission: str) -> Path:
    summary = {
        "frames": len(df),
        "leaf_coverage_pct_mean": float(df["leaf_coverage_pct"].mean(skipna=True)),
        "leaf_coverage_pct_median": float(df["leaf_coverage_pct"].median(skipna=True)),
        "ripe_mean": float(df["ripe"].mean(skipna=True)) if "ripe" in df else np.nan,
        "unripe_mean": float(df["unripe"].mean(skipna=True)) if "unripe" in df else np.nan,
        "fruit_count_mean": float(df["fruit_count"].mean(skipna=True)) if "fruit_count" in df else np.nan,
        "stains_area_pct_mean": float(df["stains_area_pct"].mean(skipna=True)) if "stains_area_pct" in df else np.nan,
        "sharpness_laplacian_median": float(df["sharpness_laplacian"].median(skipna=True)) if "sharpness_laplacian" in df else np.nan,
    }
    p = out_dir / f"{mission}_summary.csv"
    pd.DataFrame([summary]).to_csv(p, index=False)
    return p

def _fmt_time_axis(ax: plt.Axes):
    ax.tick_params(axis='x', rotation=25)

def _choose_x(df: pd.DataFrame, prefer: str = "auto") -> tuple[str, str]:
    """
    Devuelve (x_col, label) según disponibilidad. 'auto' usa tiempo
    salvo que todas las tomas sean del mismo día/instante.
    """
    if prefer == "frame":
        return "frame_idx", "Orden de frame"
    if prefer == "time":
        return "ts", "Tiempo"
    # auto
    if df["ts"].notna().any() and not _same_day_or_identical_ts(df["ts"]):
        return "ts", "Tiempo"
    return "frame_idx", "Orden de frame"

# --------- Gráficas ----------------------------------------------------------
def plot_line(df: pd.DataFrame, x: str, y: str, title: str, xlabel: str, ylabel: str, out: Path):
    fig = plt.figure()
    ax = plt.gca()
    ax.plot(df[x], df[y])
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if x == "ts":
        _fmt_time_axis(ax)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)

def plot_dual_line(df: pd.DataFrame, x: str, y1: str, y2: str, title: str, xlabel: str, ylabel: str, legend: tuple[str,str], out: Path):
    fig = plt.figure()
    ax = plt.gca()
    ax.plot(df[x], df[y1], label=legend[0])
    ax.plot(df[x], df[y2], label=legend[1])
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    if x == "ts":
        _fmt_time_axis(ax)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)

def plot_hist(df: pd.DataFrame, col: str, bins: int, title: str, xlabel: str, out: Path):
    fig = plt.figure()
    ax = plt.gca()
    ax.hist(df[col].dropna(), bins=bins)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Frecuencia")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)

def plot_scatter_with_trend(df: pd.DataFrame, x: str, y: str, title: str, xlabel: str, ylabel: str, out: Path):
    data = df[[x, y]].dropna()
    fig = plt.figure()
    ax = plt.gca()
    ax.scatter(data[x], data[y])
    if len(data) >= 2:
        coeffs = np.polyfit(pd.to_numeric(data[x], errors="coerce"), data[y], 1)
        xx = np.linspace(pd.to_numeric(data[x], errors="coerce").min(),
                         pd.to_numeric(data[x], errors="coerce").max(), 100)
        yy = coeffs[0] * xx + coeffs[1]
        ax.plot(xx, yy)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)

def plot_stacked_normalized(df: pd.DataFrame, x: str, y_r: str, y_u: str, title: str, xlabel: str, out: Path):
    data = df[[x, y_r, y_u]].fillna(0).copy()
    data["total"] = data[y_r] + data[y_u]
    data = data[data["total"] > 0]
    if data.empty:
        return
    data["p_unripe"] = data[y_u] / data["total"]
    data["p_ripe"] = data[y_r] / data["total"]

    fig = plt.figure(figsize=(12, 6))
    ax = plt.gca()
    ax.bar(data[x], data["p_unripe"], label="Verde")
    ax.bar(data[x], data["p_ripe"], bottom=data["p_unripe"], label="Maduro")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Proporción")
    ax.legend()
    if x == "ts":
        _fmt_time_axis(ax)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)

def plot_bar_counts(series: pd.Series, title: str, xlabel: str, ylabel: str, out: Path):
    counts = series.value_counts(dropna=False)
    fig = plt.figure()
    ax = plt.gca()
    ax.bar(counts.index.astype(str), counts.values)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)

# --------- Pipeline de reporte ----------------------------------------------
def build_charts(df: pd.DataFrame, mission: str, out_dir: Path, x_pref: str = "auto") -> List[Path]:
    outputs: List[Path] = []
    ensure_out(out_dir)

    csvp = save_csv(df, out_dir, f"{mission}_frames_metrics")
    outputs.append(csvp)
    outputs.append(save_summary(df, out_dir, mission))

    xcol, xlabel = _choose_x(df, x_pref)

    # 1) Cobertura vs X + media móvil
    if df["leaf_coverage_pct"].notna().any():
        dd = df.dropna(subset=["leaf_coverage_pct"]).copy()
        dd["cov_roll5"] = dd["leaf_coverage_pct"].rolling(window=5, min_periods=1).mean()
        p = out_dir / f"{mission}_leaf_coverage_over_{xcol}.png"
        fig = plt.figure()
        ax = plt.gca()
        ax.plot(dd[xcol], dd["leaf_coverage_pct"], label="Cobertura (%)")
        ax.plot(dd[xcol], dd["cov_roll5"], label="Media móvil (5)")
        ax.set_title(f"Cobertura foliar – {mission}")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Cobertura (%)")
        ax.legend()
        if xcol == "ts":
            _fmt_time_axis(ax)
        fig.tight_layout()
        fig.savefig(p, dpi=150)
        plt.close(fig)
        outputs.append(p)

    # 2) Frutos (maduro/verde) vs X
    if df[["ripe","unripe"]].notna().any().any():
        p = out_dir / f"{mission}_ripe_unripe_over_{xcol}.png"
        plot_dual_line(df.dropna(subset=[xcol]), xcol, "ripe", "unripe",
                       f"Frutos maduros vs verdes – {mission}", xlabel, "Conteo", ("Maduros","Verdes"), p)
        outputs.append(p)

        # 2b) Composición normalizada
        p2 = out_dir / f"{mission}_ripe_composition_over_{xcol}.png"
        plot_stacked_normalized(df, xcol, "ripe", "unripe",
                                f"Composición de madurez (normalizado) – {mission}",
                                xlabel, p2)
        outputs.append(p2)

    # 3) Manchas en hoja vs X
    if df["stains_area_pct"].notna().any():
        p = out_dir / f"{mission}_leaf_stains_over_{xcol}.png"
        plot_line(df.dropna(subset=[xcol,"stains_area_pct"]), xcol, "stains_area_pct",
                  f"Área de manchas en hoja – {mission}", xlabel, "Área manchas (%)", p)
        outputs.append(p)

    # 4) Histograma de nitidez
    if df["sharpness_laplacian"].notna().any():
        n = df["sharpness_laplacian"].dropna().shape[0]
        bins = min(40, max(10, int(math.sqrt(n or 1) * 2)))
        p = out_dir / f"{mission}_sharpness_hist.png"
        plot_hist(df, "sharpness_laplacian", bins,
                  f"Distribución de nitidez (Laplaciano) – {mission}", "Var(Laplaciano)", p)
        outputs.append(p)

    # 5) Cobertura vs conteo de frutos (dispersión)
    if df[["leaf_coverage_pct","fruit_count"]].notna().all(axis=1).any():
        p = out_dir / f"{mission}_scatter_leaf_vs_fruit.png"
        plot_scatter_with_trend(df, "leaf_coverage_pct", "fruit_count",
                                f"Cobertura vs Conteo de frutos – {mission}",
                                "Cobertura (%)", "Frutos (conteo)", p)
        outputs.append(p)

    # 6) Severidad de manchas (barras)
    if df["stains_area_pct"].notna().any():
        def sev(pct):
            if pd.isna(pct): return np.nan
            if pct >= 10: return "alta"
            if pct >= 5:  return "media"
            return "baja"
        sev_series = df["stains_area_pct"].apply(sev)
        p = out_dir / f"{mission}_stain_severity_bar.png"
        plot_bar_counts(sev_series, f"Severidad de manchas – {mission}", "Severidad", "Frames", p)
        outputs.append(p)

    # 7) % madurez vs X
    if df["ripe_pct"].notna().any():
        p = out_dir / f"{mission}_ripe_pct_over_{xcol}.png"
        plot_line(df.dropna(subset=[xcol,"ripe_pct"]), xcol, "ripe_pct",
                  f"Porcentaje de madurez – {mission}", xlabel, "Madurez (%)", p)
        outputs.append(p)

    return outputs

# --------- CLI ---------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generador de gráficas para frames de una misión")
    ap.add_argument("--mission", required=True, help="Nombre de la misión")
    ap.add_argument("--out", default="./reports", help="Carpeta de salida")
    ap.add_argument("--date-from", help="ISO 8601 (ej: 2025-10-01T00:00:00-05:00)")
    ap.add_argument("--date-to", help="ISO 8601")
    ap.add_argument("--limit", type=int, help="Límite de documentos")
    ap.add_argument("--x-axis", choices=["auto","time","frame"], default="auto",
                    help="Eje X: auto (default), time (ts) o frame (orden)")
    args = ap.parse_args(argv)

    out_dir = Path(args.out) / args.mission
    out_dir.mkdir(parents=True, exist_ok=True)

    df = fetch_frames(args.mission, args.date_from, args.date_to, args.limit)
    if df.empty:
        print("[WARN] No se encontraron documentos en Mongo para esa misión/rango.")
        return 0

    outs = build_charts(df, args.mission, out_dir, x_pref=args.x_axis)
    print("\nArchivos generados:")
    for p in outs:
        print(" -", p)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
