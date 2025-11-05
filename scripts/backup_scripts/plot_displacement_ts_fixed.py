#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import glob
import warnings
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import pandas as pd
import h5py as h5
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# -----------------------
# Path config (edit here)
# -----------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IN_CSV   = os.path.join(BASE_DIR, "data", "2018-2022石羊河监测井数据_水位.csv")
H5_GLOB  = os.path.join(BASE_DIR, "data", "*.h5")
OUT_DIR  = os.path.join(BASE_DIR, "Outputs", "ts_combined")
PLOTS_DIR= os.path.join(OUT_DIR, "plots")
SLOPE_CSV= os.path.join(OUT_DIR, "slopes.csv")

# A/D frame pairs (prefix matching)
FRAME_PAIRS = [
    ("128A_05172","033D_05106"),
    ("055A_05021","135D_05023"),
    ("055A_05221","135D_05222"),
]

# -----------------------
# Utilities
# -----------------------
def make_dir(*paths):
    for p in paths:
        os.makedirs(p, exist_ok=True)

def _safe_name(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", str(s))

# -----------------------
# CSV loader
# -----------------------
def load_csv(in_csv: str) -> pd.DataFrame:
    """Load the groundwater CSV and return a long table with columns:
       ['well_id','year','date','obs_date','gw_level_m','lon','lat','elevation_m']
    """
    try:
        df = pd.read_csv(in_csv, dtype=str, low_memory=False)
    except UnicodeDecodeError:
        print(f"[error] CSV 不是 UTF-8 编码：{in_csv}")
        raise

    df.columns = df.columns.str.strip()

    # rename if present
    rename_map = {
        "统一编号": "well_id",
        "年份": "year",
        "经度": "lon",
        "纬度": "lat",
        "地面高程/米": "elevation_m",
        "地面高程": "elevation_m",
        "海拔": "elevation_m",
        "高程": "elevation_m",
    }
    exist_rename = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=exist_rename)

    for col in ["well_id", "year"]:
        if col not in df.columns:
            raise KeyError(f"缺少必需列：{col}")

    # day columns like M01_D15
    pattern = re.compile(r"^M\d{2}_D\d{2}$")
    day_cols = [c for c in df.columns if pattern.match(str(c))]
    if not day_cols:
        # return empty long table skeleton
        return pd.DataFrame(columns=[
            "well_id","year","date","obs_date","gw_level_m","lon","lat","elevation_m"
        ])

    id_vars = [c for c in ["well_id","year","lon","lat","elevation_m"] if c in df.columns]

    df_long = df.melt(
        id_vars=id_vars,
        value_vars=day_cols,
        var_name="obs_date",
        value_name="gw_level_m"
    )

    # numeric conversions
    df_long["gw_level_m"] = pd.to_numeric(df_long["gw_level_m"], errors="coerce")
    for c in ["year","lon","lat","elevation_m"]:
        if c in df_long.columns:
            df_long[c] = pd.to_numeric(
                df_long[c].astype(str).str.replace("\u3000"," ", regex=False).str.strip(),
                errors="coerce"
            )

    # build proper datetime from year + obs_date
    md = df_long["obs_date"].str.extract(r"M(\d{2})_D(\d{2})").astype(float)
    df_long["month"] = md[0]
    df_long["day"]   = md[1]

    df_long = df_long.dropna(subset=["year","month","day"])
    df_long["date"] = pd.to_datetime(
        {
            "year":  df_long["year"].astype(int),
            "month": df_long["month"].astype(int),
            "day":   df_long["day"].astype(int),
        },
        errors="coerce"
    )
    df_long = df_long.dropna(subset=["date"]).reset_index(drop=True)

    # reorder columns
    cols = ["well_id","year","date","obs_date","gw_level_m","lon","lat","elevation_m"]
    df_long = df_long[[c for c in cols if c in df_long.columns]]
    return df_long

# -----------------------
# H5 metadata + helpers
# -----------------------
def scan_h5_meta(h5_path: str) -> Dict[str, Any]:
    """Read only small metadata needed for coverage test and indexing."""
    with h5.File(h5_path, "r") as f:
        ny, nx = f["cum"].shape[1], f["cum"].shape[2]
        corner_lon = float(f["corner_lon"][()])
        post_lon   = float(f["post_lon"][()])
        corner_lat = float(f["corner_lat"][()])
        post_lat   = float(f["post_lat"][()])

    lon_last = corner_lon + (nx - 1) * post_lon
    lat_last = corner_lat + (ny - 1) * post_lat
    lon_min, lon_max = (min(corner_lon, lon_last), max(corner_lon, lon_last))
    lat_min, lat_max = (min(corner_lat, lat_last), max(corner_lat, lat_last))

    return dict(
        path=h5_path,
        base=os.path.basename(h5_path),
        nx=nx, ny=ny,
        corner_lon=corner_lon, post_lon=post_lon,
        corner_lat=corner_lat, post_lat=post_lat,
        lon_min=lon_min, lon_max=lon_max,
        lat_min=lat_min, lat_max=lat_max,
    )

def point_in_meta(meta: Dict[str,Any], lon: float, lat: float, eps: float=1e-12) -> bool:
    return (meta["lon_min"] - eps <= lon <= meta["lon_max"] + eps) and \
           (meta["lat_min"] - eps <= lat <= meta["lat_max"] + eps)

def coord_to_index(start: float, post: float, n: int, coord: float) -> int:
    if post == 0:
        return 0
    ix = int(round((coord - start) / post))
    return max(0, min(n - 1, ix))

def which_pair_and_side(base: str) -> Tuple[Optional[str], Optional[str]]:
    for a, d in FRAME_PAIRS:
        if base.startswith(a): return f"{a}__{d}", "A"
        if base.startswith(d): return f"{a}__{d}", "D"
    return None, None

# -----------------------
# Extract one point time-series from H5
# -----------------------
def load_hdf5_point(h5_path: str, lon_pt: float, lat_pt: float) -> pd.DataFrame:
    with h5.File(h5_path, "r") as f:
        ny, nx = f["cum"].shape[1], f["cum"].shape[2]
        corner_lon = float(f["corner_lon"][()])
        post_lon   = float(f["post_lon"][()])
        corner_lat = float(f["corner_lat"][()])
        post_lat   = float(f["post_lat"][()])

        ix = coord_to_index(corner_lon, post_lon, nx, lon_pt)
        iy = coord_to_index(corner_lat, post_lat, ny, lat_pt)

        ts = f["cum"][:, iy, ix]  # cumulative displacement time series
        imdates = f["imdates"][:] if "imdates" in f else np.arange(ts.shape[0])

    dt = pd.to_datetime(imdates.astype(str), format="%Y%m%d", errors="coerce")
    df = pd.DataFrame({
        "date": dt,
        "displacement": ts.astype(float),
        "lon": lon_pt, "lat": lat_pt,
        "ix": ix, "iy": iy,
        "h5": os.path.basename(h5_path),
    }).dropna(subset=["date"])
    return df

# -----------------------
# Robust WLS (two-pass)
# -----------------------
def _to_decimal_year(dts: pd.Series) -> np.ndarray:
    dts = pd.to_datetime(dts)
    y = dts.dt.year.values
    start = pd.to_datetime(pd.Series(y).astype(str) + "-01-01")
    end   = pd.to_datetime(pd.Series(y).astype(str) + "-12-31")
    days = (end - start).dt.days.replace(0, 365).values
    frac = (dts - start.values).days / days
    return y + frac

def wls_two_pass(df: pd.DataFrame, x_col="date", y_col="displacement"):
    """Return slope/intercept and fitted values; None if not enough points."""
    import statsmodels.api as sm
    EPS = 1e-9
    K = 1.345
    if df is None or df.empty:
        return None
    X = pd.to_datetime(df[x_col])
    y = pd.to_numeric(df[y_col], errors="coerce")
    m = X.notna() & y.notna()
    X = X[m]; y = y[m]
    if len(X) < 3:
        return None

    Xd = _to_decimal_year(X)
    Xsm = sm.add_constant(Xd)

    # OLS
    ols = sm.OLS(y.values, Xsm).fit()
    b0, m0 = ols.params
    resid = y.values - (b0 + m0*Xd)
    mad = np.median(np.abs(resid - np.median(resid))) + EPS
    s = 1.4826 * mad
    u = resid / s
    w = np.where(np.abs(u) <= K, 1.0, K/(np.abs(u)+EPS)) * (1.0/(np.abs(u)+EPS))
    w = np.clip(w, 1e-3, None)

    wls1 = sm.WLS(y.values, Xsm, weights=w).fit()
    b1, m1 = wls1.params

    resid = y.values - (b1 + m1*Xd)
    mad = np.median(np.abs(resid - np.median(resid))) + EPS
    s = 1.4826 * mad
    u = resid / s
    w = np.where(np.abs(u) <= K, 1.0, K/(np.abs(u)+EPS)) * (1.0/(np.abs(u)+EPS))
    w = np.clip(w, 1e-3, None)

    wls2 = sm.WLS(y.values, Xsm, weights=w).fit()
    b2, m2 = wls2.params
    fitted = b2 + m2*Xd
    return {"x": pd.to_datetime(X), "y": y.values, "fitted": fitted, "slope": m2, "intercept": b2}

# -----------------------
# Plot A, D, and GW in one figure
# -----------------------
def plot_ad_gw(well_id: str,
               dfA: pd.DataFrame,
               dfD: pd.DataFrame,
               dfGW: pd.DataFrame,
               save_path: str,
               elev: Optional[float] = None):
    fig, ax_gw = plt.subplots(figsize=(12,7), dpi=180)
    ax_insar = ax_gw.twinx()

    # GW (left axis)
    if dfGW is not None and not dfGW.empty:
        dfGW = dfGW.sort_values("date")
        ax_gw.scatter(dfGW["date"], dfGW["gw_level_m"], s=20, alpha=0.6, label="Groundwater (m)")
        fitGW = wls_two_pass(dfGW.rename(columns={"gw_level_m":"displacement"}), x_col="date", y_col="displacement")
        if fitGW:
            ax_gw.plot(fitGW["x"], fitGW["fitted"], lw=1.8, label=f"GW WLS (slope={fitGW['slope']:.3f} m/yr)")

    # A (right axis)
    if dfA is not None and not dfA.empty:
        dfA = dfA.sort_values("date")
        ax_insar.scatter(dfA["date"], dfA["displacement"], s=18, alpha=0.6, label="A (mm)")
        fitA = wls_two_pass(dfA, x_col="date", y_col="displacement")
        if fitA:
            ax_insar.plot(fitA["x"], fitA["fitted"], lw=1.8, label=f"A WLS (slope={fitA['slope']:.2f} mm/yr)")
    else:
        fitA = None

    # D (right axis)
    if dfD is not None and not dfD.empty:
        dfD = dfD.sort_values("date")
        ax_insar.scatter(dfD["date"], dfD["displacement"], s=18, alpha=0.6, label="D (mm)")
        fitD = wls_two_pass(dfD, x_col="date", y_col="displacement")
        if fitD:
            ax_insar.plot(fitD["x"], fitD["fitted"], lw=1.8, label=f"D WLS (slope={fitD['slope']:.2f} mm/yr)")
    else:
        fitD = None

    title = f"Well {well_id} — A&D vs GW"
    if elev is not None and np.isfinite(elev):
        title += f" | Elev: {elev:.2f} m"
    ax_gw.set_title(title)

    ax_gw.set_xlabel("Date")
    ax_gw.set_ylabel("Groundwater level (m)")
    ax_insar.set_ylabel("Cumulative LOS displacement (mm)")

    ax_gw.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax_gw.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax_gw.xaxis.get_major_locator()))

    # legends
    h1, l1 = ax_gw.get_legend_handles_labels()
    h2, l2 = ax_insar.get_legend_handles_labels()
    if h1 or h2:
        ax_insar.legend((h1+h2), (l1+l2), loc="upper left", frameon=False)

    fig.tight_layout()
    fig.savefig(save_path, dpi=180)
    plt.close(fig)

    # return slopes for CSV
    slopeA = float(fitA["slope"]) if fitA else np.nan
    slopeD = float(fitD["slope"]) if fitD else np.nan
    slopeGW = float(fitGW["slope"]) if (dfGW is not None and not dfGW.empty) and fitGW else np.nan
    return slopeA, slopeD, slopeGW

# -----------------------
# Main pipeline
# -----------------------
def main():
    warnings.filterwarnings("ignore")
    make_dir(OUT_DIR, PLOTS_DIR)

    # 1) CSV
    df_csv_long = load_csv(IN_CSV)
    if df_csv_long.empty:
        print("[warn] df_csv_long is empty."); return

    # 2) H5 metas
    h5_paths = sorted(glob.glob(H5_GLOB))
    if not h5_paths:
        print(f"[warn] no H5 files found at: {H5_GLOB}"); return
    metas = [scan_h5_meta(p) for p in h5_paths]

    # 3) Build tasks: for each well, find covering H5 then group by A/D pair
    tasks: List[Tuple[str, float, float, str, List[Dict[str,Any]], List[Dict[str,Any]]]] = []
    for well_id, g in df_csv_long.groupby("well_id"):
        if not {"lon","lat"}.issubset(g.columns):
            continue
        if g["lon"].notna().any() and g["lat"].notna().any():
            lon_pt = float(g["lon"].dropna().iloc[0])
            lat_pt = float(g["lat"].dropna().iloc[0])
        else:
            continue

        covered = [m for m in metas if point_in_meta(m, lon_pt, lat_pt)]
        if not covered:
            continue

        bucket: Dict[str, Dict[str, List[Dict[str,Any]]]] = {}
        for m in covered:
            pair_key, side = which_pair_and_side(m["base"])
            if pair_key and side in ("A","D"):
                bucket.setdefault(pair_key, {}).setdefault(side, []).append(m)

        for pair_key, sides in bucket.items():
            if "A" in sides and "D" in sides:
                tasks.append((well_id, lon_pt, lat_pt, pair_key, sides["A"], sides["D"]))

    if not tasks:
        print("[info] no A&D pairs covering any well."); return

    # 4) For each task, load time series (only now), plot, and collect slopes
    rows = []
    for (well_id, lon_pt, lat_pt, pair_key, metasA, metasD) in tasks:
        # concat all A/D time series for this point
        dfA = pd.concat([load_hdf5_point(m["path"], lon_pt, lat_pt) for m in metasA], ignore_index=True)
        dfD = pd.concat([load_hdf5_point(m["path"], lon_pt, lat_pt) for m in metasD], ignore_index=True)
        dfGW = df_csv_long[df_csv_long["well_id"] == well_id][["well_id","date","gw_level_m"]].rename(columns={"gw_level_m":"gw_level_m"})

        # plot
        elev = None
        if "elevation_m" in df_csv_long.columns:
            e = df_csv_long.loc[df_csv_long["well_id"] == well_id, "elevation_m"].dropna()
            elev = float(e.iloc[0]) if len(e) else None

        save_name = f"{_safe_name(well_id)}__{_safe_name(pair_key)}.png"
        save_path = os.path.join(PLOTS_DIR, save_name)
        slopeA, slopeD, slopeGW = plot_ad_gw(well_id, dfA, dfD, dfGW, save_path, elev=elev)

        rows.append({
            "well_id": well_id,
            "pair": pair_key,
            "a_slope_mm_per_yr": slopeA,
            "d_slope_mm_per_yr": slopeD,
            "gw_slope_m_per_yr": slopeGW,
            "nA": len(dfA),
            "nD": len(dfD),
            "nGW": len(dfGW),
            "plot": save_name
        })

    out = pd.DataFrame(rows)
    out.to_csv(SLOPE_CSV, index=False, encoding="utf-8-sig")
    print(f"[ok] wrote: {SLOPE_CSV}")
    print(f"[ok] plots in: {PLOTS_DIR}")

if __name__ == "__main__":
    main()
