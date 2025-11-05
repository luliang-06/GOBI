#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import glob
import warnings
import numpy as np
import pandas as pd
import h5py
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mtick
import statsmodels.api as sm
from statsmodels.robust.norms import HuberT
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from decimal import Decimal, InvalidOperation, localcontext
import seaborn as sns

# ============ 0) 路径 & 参数 ============
IN_CSV = '/Users/lianglu/Desktop/GOBI/data/2018-2022石羊河地下水监测井数据_水位.csv'
OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Outputs/gw_diss_ts_vu'))
DATA_DIR = '/Users/lianglu/Desktop/GOBI/data'
H5_PATTERN = "*.vu.h5"
COORDS_OUT = os.path.join(OUT_DIR, 'coords_for_ts.csv')
os.makedirs(OUT_DIR, exist_ok=True)

# observation有效性
YEAR_MIN = 2014
YEAR_MAX = 2023
START_DATE = pd.Timestamp(f"{YEAR_MIN}-01-01")
END_DATE   = pd.Timestamp(f"{YEAR_MAX}-12-31")

# outlier 判定
K_HUBER = 1.345
EPS = 1e-6
MIN_WEIGHT = 1e-3
OUTLIER_SIGMA = 4.5

# 图形风格
FIGSIZE = (12, 7)
DPI = 180


VERBOSE = False

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

# ============ 1) plot theme ============
sns.set_theme(style="whitegrid", context="talk", rc={"grid.linewidth": 0.8})
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']

plt.rcParams['xtick.labelsize'] = 12
plt.rcParams['ytick.labelsize'] = 12

# ============ 2) functions ============
# 安全文件名（option）
def _safe_name(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', '_', str(s))

def _ensure_dirs(*paths):
    for p in paths:
        os.makedirs(p, exist_ok=True)

def _dates_to_datetime(arr):
    def parse_one(x):
        s = x.decode() if isinstance(x, (bytes, np.bytes_)) else str(x)
        s = s.strip()
        for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d"):
            try: return datetime.strptime(s, fmt)
            except: pass
        digits = "".join(ch for ch in s if ch.isdigit())
        if len(digits)==8:
            try: return datetime.strptime(digits, "%Y%m%d")
            except: pass
        return pd.NaT
    return pd.to_datetime([parse_one(v) for v in arr])

def _find_ds_path(f: h5py.File, names) -> Optional[str]:
    want = {n.lower() for n in names}
    for k in f.keys():
        if k.lower() in want:
            return k
    def dfs(g, prefix=""):
        for k, v in g.items():
            p = f"{prefix}/{k}" if prefix else k
            if isinstance(v, h5py.Dataset) and k.lower() in want:
                return p
            if isinstance(v, h5py.Group):
                got = dfs(v, p)
                if got: return got
        return None
    return dfs(f)

def _read_ds(f: h5py.File, path: str):
    obj = f
    for p in path.split("/"):
        obj = obj[p]
    return obj[...]

def _get_scalar(f: h5py.File, names):
    path = _find_ds_path(f, names)
    if not path:
        raise KeyError(f"Missing dataset among {names}")
    val = _read_ds(f, path)
    return float(val)

def _find_time_axis(cum_shape: Tuple[int,int,int], ntime: Optional[int]) -> int:
    if ntime is not None and ntime in cum_shape:
        return list(cum_shape).index(ntime)
    return 2

def _extent_from_corner_post(corner: float, post: float, n: int) -> Tuple[float,float]:
    last = corner + (n - 1) * post
    return (min(corner, last), max(corner, last))

def _in_extent(coord: float, lo: float, hi: float, eps=1e-10) -> bool:
    return (coord >= lo - eps) and (coord <= hi + eps)

def _clamp_to_pixel(corner: float, post: float, coord: float, n: int) -> int:
    if post == 0:
        return 0
    ix = int(round((coord - corner) / post))
    return max(0, min(n-1, ix))

def normalize_id_series(s: pd.Series) -> pd.Series:
    def _one(x):
        if pd.isna(x):
            return ""
        txt = str(x).strip().replace(",", "")  # 去千分位逗号
        if txt == "":
            return ""
        try:
            with localcontext() as ctx:
                ctx.prec = 80  # 足够高的精度，避免截断
                d = Decimal(txt)
                if d == d.to_integral_value():
                    return format(d.quantize(Decimal(1)), "f")
                else:
                    out = format(d.normalize(), "f")
                    if "." in out:
                        out = out.rstrip("0").rstrip(".")
                    return out
        except InvalidOperation:
            return txt
    return s.apply(_one)


def _finite_minmax(arr: np.ndarray) -> Tuple[float, float]:
    """在可能包含 NaN 的数组上取有限值范围；全 NaN 则抛错。"""
    mask = np.isfinite(arr)
    if not mask.any():
        raise ValueError("all values are NaN")
    vals = arr[mask]
    return float(vals.min()), float(vals.max())

# ============ 3) Step A: 从input csv中抽出 id/lon/lat ============
def build_coords_from_big_csv_simple(in_csv: str, out_csv: str,
                                     id_col='统一编号', lon_col='经度', lat_col='纬度') -> pd.DataFrame:
    def _read(path):
        try:
            return pd.read_csv(path, sep=',', engine='c', dtype=str, low_memory=False)
        except UnicodeDecodeError:
            return pd.read_csv(path, sep=',', engine='c', dtype=str, low_memory=False, encoding='gbk')

    df = _read(in_csv)
    if df.empty:
        raise ValueError(f'输入CSV为空：{in_csv}')

    df.columns = [str(c).strip() for c in df.columns]

    miss = [c for c in (id_col, lon_col, lat_col) if c not in df.columns]
    if miss:
        sample_cols = list(df.columns)[:20]
        raise KeyError(f'缺少必需列：{miss}；CSV 实际列名前20个：{sample_cols}')

    sub = df[[id_col, lon_col, lat_col]].copy()
    sub = sub.rename(columns={id_col: 'id', lon_col: 'lon', lat_col: 'lat'})

    sub['id'] = normalize_id_series(sub['id'])

    def _to_num(s):
        s = s.astype(str).str.replace('\u3000', ' ', regex=False).str.strip()
        return pd.to_numeric(s, errors='coerce')
    sub['lon'] = _to_num(sub['lon'])
    sub['lat'] = _to_num(sub['lat'])

    elev_candidates = [c for c in df.columns if re.search(r'(地面高程/米|地面高程|海拔|高程)', str(c))]
    if elev_candidates:
        elev_src = elev_candidates[0]
        elev_series = (
            df[elev_src].astype(str)
            .str.extract(r'([-+]?\d*\.?\d+)')[0]     # 只取数值部分
        )
        sub['elevation_m'] = pd.to_numeric(elev_series, errors='coerce')
    
    m = sub['lon'].between(-180, 180) & sub['lat'].between(-90, 90)
    sub = sub[m & sub['lon'].notna() & sub['lat'].notna()]

    if sub.empty:
        raise ValueError('三列已读取，但没有通过经纬度清洗/范围过滤的有效行。请检查经纬度格式（是否为小数度）。')

    sub = sub.drop_duplicates(subset=['id'], keep='first').reset_index(drop=True)

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    sub.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f'已保存坐标清单：{out_csv} （{len(sub)} 行）')
    return sub

# ============ 4) Step B: 扫描 H5 数据，提取并作图 ============
def scan_vu_meta(h5_path: str) -> Dict[str, Any]:
    """读取 *.vu.h5 的最小元数据，容忍 lon/lat 缺失或全 NaN，必要时退回 corner/post 推算。"""
    base = os.path.basename(h5_path)
    with h5py.File(h5_path, "r") as f:
        # 必备：/vu
        if "vu" not in f:
            raise KeyError(f"{base}: missing dataset 'vu'")
        vu_shape = tuple(f["vu"].shape)   # 3D

        # 尝试优先用 lon/lat
        have_lonlat = ("lon" in f) and ("lat" in f)
        H = W = None
        lon_min = lon_max = lat_min = lat_max = None

        if have_lonlat:
            lon2d = f["lon"][:]   # (H,W)
            lat2d = f["lat"][:]
            if lon2d.ndim != 2 or lat2d.ndim != 2:
                raise ValueError(f"{base}: lon/lat must be 2D, got {lon2d.shape}/{lat2d.shape}")
            H, W = lon2d.shape
            try:
                lon_min, lon_max = _finite_minmax(lon2d)
                lat_min, lat_max = _finite_minmax(lat2d)
            except ValueError:
                # 全 NaN → 退回 corner/post
                have_lonlat = False

        # 若没有 lon/lat（或全 NaN），用 corner/post + (H,W) 推算范围
        if not have_lonlat:
            need = ["corner_lon", "corner_lat", "post_lon", "post_lat"]
            if not all(k in f for k in need):
                raise KeyError(f"{base}: missing lon/lat and also missing corner/post")
            corner_lon = float(f["corner_lon"][()])
            corner_lat = float(f["corner_lat"][()])
            post_lon   = float(f["post_lon"][()])
            post_lat   = float(f["post_lat"][()])

            if len(vu_shape) != 3:
                raise ValueError(f"{base}: vu must be 3D, got {vu_shape}")

            # 先假定最后两维是空间（与你写TIF的习惯一致）
            H, W = vu_shape[1], vu_shape[2]
            lon_last = corner_lon + (W - 1) * post_lon
            lat_last = corner_lat + (H - 1) * post_lat
            lon_min, lon_max = (min(corner_lon, lon_last), max(corner_lon, lon_last))
            lat_min, lat_max = (min(corner_lat, lat_last), max(corner_lat, lat_last))

        # 判定时间轴：与 (H,W) 匹配的那种
        if vu_shape[1:] == (H, W):
            t_ax = 0              # (T,H,W)
        elif vu_shape[:2] == (H, W):
            t_ax = 2              # (H,W,T)
        else:
            raise ValueError(f"{base}: vu shape {vu_shape} not compatible with (H,W)=({H},{W})")

        # 时间长度（若有 imdates）
        dates_path = "imdates" if "imdates" in f else None
        ntime = int(np.size(f["imdates"])) if dates_path else None

    return dict(
        path=h5_path,
        base=base,
        lon_min=lon_min, lon_max=lon_max,
        lat_min=lat_min, lat_max=lat_max,
        vu_shape=vu_shape,
        t_ax=t_ax,
        dates_path=dates_path,
        ntime=ntime,
    )


def extract_and_plot(meta: Dict[str, Any], lon: float, lat: float, ident: Optional[str],
                      out_root: str, figsize=(12,7), dpi=180, do_plot_single=False):
    """
    适配当前 vu.h5 结构：
      - Datasets:
          /vu        -> 3D (T,H,W) 或 (H,W,T)
          /lon,/lat  -> 2D (H,W)
          /imdates   -> 1D (T,)
          /corner_*, /post_* 可有可无
    """
    import pandas as pd
    import matplotlib.pyplot as plt

    with h5py.File(meta["path"], "r") as f:
        # 读必要数据
        vu_ds = f["vu"]                # 3D
        lon2d = f["lon"][:]            # (H,W)
        lat2d = f["lat"][:]            # (H,W)
        H, W  = lon2d.shape

        # 读时间轴
        if "imdates" in f:
            dates_raw = f["imdates"][:]
        else:
            # 没有的话，用 T 序号占位
            T_guess = vu_ds.shape[0] if vu_ds.shape[1:] == (H, W) else vu_ds.shape[-1]
            dates_raw = np.arange(T_guess)

        # 判定 vu 的时间轴位置
        if vu_ds.shape[1:] == (H, W):
            # (T,H,W)
            t_ax = 0
            T = vu_ds.shape[0]
        elif vu_ds.shape[:2] == (H, W):
            # (H,W,T)
            t_ax = 2
            T = vu_ds.shape[2]
        else:
            raise ValueError(f"vu shape {vu_ds.shape} not compatible with lon/lat {(H,W)}")

        # 用边上的一条剖面当作一维坐标，找最近像元索引
        x_coords = lon2d[0, :]           # 长度 W
        y_coords = lat2d[:, 0]           # 长度 H

        # 注意：lat 可能递减（post_lat < 0），所以找最近要用 argmin(|diff|)
        ix = int(np.argmin(np.abs(x_coords - lon)))
        iy = int(np.argmin(np.abs(y_coords - lat)))

        # 实际像元中心坐标
        lon_pix = float(x_coords[ix])
        lat_pix = float(y_coords[iy])

        # 取该像元的时间序列
        if t_ax == 0:     # (T,H,W)
            ts = vu_ds[:, iy, ix]
        else:             # (H,W,T)
            ts = vu_ds[iy, ix, :]

        # 转时间
        dt = pd.to_datetime(dates_raw, errors="coerce")
        dt_s = pd.Series(dt)

    # 有些值可能是 NaN；同时尊重你的全局时间窗（若存在）
    ok = np.isfinite(ts) & dt_s.notna()
    if "START_DATE" in globals() and "END_DATE" in globals():
        ok = ok & dt_s.between(START_DATE, END_DATE, inclusive="both")

    if not np.any(ok):
        return None, None

    df_ts = pd.DataFrame({
        "id":  ident if ident is not None else "",
        "lon": float(lon),
        "lat": float(lat),
        "date": dt_s[ok].values,
        "displacement": np.asarray(ts)[ok],
        "h5": meta.get("base", os.path.basename(meta["path"])),
        "ix": int(ix),
        "iy": int(iy),
        "pix_lon": lon_pix,
        "pix_lat": lat_pix,
    })

    # 可选：单点 quick plot（简单直观）
    if do_plot_single:
        plt.figure(figsize=figsize, dpi=dpi)
        plt.plot(df_ts["date"], df_ts["displacement"], marker="o", lw=1)
        plt.xlabel("Date")
        plt.ylabel("Vertical cumulative displacement (same unit as vu)")
        title_id = ident if ident is not None else ""
        plt.title(f"{meta.get('base', os.path.basename(meta['path']))}  ix={ix}, iy={iy}  {title_id}")
        plt.grid(True, ls="--", alpha=0.4)
        os.makedirs(out_root, exist_ok=True)
        out_png = os.path.join(out_root, f"{meta.get('base','vu')}_ix{ix}_iy{iy}.png")
        plt.tight_layout()
        plt.savefig(out_png)
        plt.close()

    return df_ts, (ix, iy)


def _to_decimal_year(dts):
    dts = pd.to_datetime(dts)
    y = dts.dt.year.astype(int)
    start = pd.to_datetime(y.astype(str) + '-01-01')
    end   = pd.to_datetime(y.astype(str) + '-12-31')
    days = (end - start).dt.days.replace(0, 365)
    frac = (dts - start).dt.days / days
    return y + frac

def _wls_two_pass(df, x_col='date', y_col='displacement'):
    if df.empty:
        return None
    X = _to_decimal_year(pd.to_datetime(df[x_col]))
    y = pd.to_numeric(df[y_col], errors='coerce')
    mask = (~X.isna()) & (~y.isna()) & (~np.isinf(y)) & (~np.isinf(X))
    X = X[mask].astype(float)
    y = y[mask].astype(float)
    if len(X) < 3:
        return None
    
    X_sm = sm.add_constant(X.values)

    # OLS fit
    ols_res = sm.OLS(y.values, X_sm).fit()
    b0, m0 = ols_res.params

    # 1st WLS
    resid0 = y.values - (b0 + m0 * X.values)
    mad0 = np.median(np.abs(resid0 - np.median(resid0)))
    s0 = 1.4826 * mad0 + EPS
    u0 = resid0 / s0
    # Huber 权重
    w_huber0 = np.where(np.abs(u0) <= K_HUBER, 1.0, K_HUBER / (np.abs(u0) + EPS))
    # L1 风格权重
    w_l1_0 = 1.0 / (np.abs(u0) + EPS)
    # 组合权重（更强鲁棒）：两者相乘
    w1 = np.clip(w_huber0 * w_l1_0, MIN_WEIGHT, None)

    wls1 = sm.WLS(y.values, X_sm, weights=w1).fit()
    b1, m1 = wls1.params

    # 2nd WLS
    resid1 = y.values - (b1 + m1 * X.values)
    mad1 = np.median(np.abs(resid1 - np.median(resid1)))
    s1 = 1.4826 * mad1 + EPS
    u1 = resid1 / s1

    w_huber1 = np.where(np.abs(u1) <= K_HUBER, 1.0, K_HUBER / (np.abs(u1) + EPS))
    w_l1_1 = 1.0 / (np.abs(u1) + EPS)
    w2 = np.clip(w_huber1 * w_l1_1, MIN_WEIGHT, None)

    wls2 = sm.WLS(y.values, X_sm, weights=w2).fit()
    b2, m2 = wls2.params
    m2_err = wls2.bse[1] if hasattr(wls2, 'bse') and len(wls2.bse) > 1 else np.nan
    resid_final = y.values - (b2 + m2 * X.values)
    thr = np.mean(np.abs(resid_final)) + OUTLIER_SIGMA * np.std(np.abs(resid_final))
    is_out = np.abs(resid_final) > thr
    fitted = b2 + m2 * X.values
    return {'x': pd.to_datetime(df.loc[mask, x_col].values),
            'y': y.values, 'fitted': fitted, 'mask_valid': mask.values,
            'is_outlier': is_out, 'slope': m2, 'intercept': b2, 'slope_stderr': m2_err}

def _plot_outliers_and_get_range(ax, fit: dict, color='red', marker='X', s=100, edgecolor='black', linewidth=1.0, 
                                 label: str | None = None, zoom_margin=0.10):
    """
    用 WLS 结果中的 outlier 掩码在 ax 上标注异常点，并返回“主数据”的 y 轴建议范围。
    返回: (ymin, ymax) 或 None（当没有 outlier 时）
    """
    if fit is None or 'is_outlier' not in fit:
        return None

    is_out = np.asarray(fit['is_outlier'])
    y_all  = np.asarray(fit['y'])
    x_all  = pd.to_datetime(fit['x'])

    # 标注异常点
    if is_out.any():
        xo = x_all[is_out]
        yo = y_all[is_out]
        sns.scatterplot(x=xo, y=yo, ax=ax,
                        marker=marker, s=s, color=color,
                        edgecolor=edgecolor, linewidth=linewidth,
                        legend=False if label is None else False,
                        label=label)
        # 计算“主数据”的范围并给出建议 ylims
        y_main = y_all[~is_out]
        if y_main.size:
            y_min, y_max = np.min(y_main), np.max(y_main)
            span = y_max - y_min
            # 防止零跨度时的极端值
            if span <= 0:
                margin = max(0.05 * max(1.0, abs(y_min)), 1e-3)
            else:
                margin = span * zoom_margin
            return (y_min - margin, y_max + margin)

    return None


def _apply_axis_zoom(ax, ranges: list[tuple[float, float]]):
    """
    将多个(ymin, ymax)建议合并后一次性设置轴范围。
    """
    if not ranges:
        return
    lows, highs = zip(*ranges)
    ylo = float(np.min(lows))
    yhi = float(np.max(highs))
    if np.isfinite(ylo) and np.isfinite(yhi) and yhi > ylo:
        ax.set_ylim(ylo, yhi)


def _load_groundwater_long(csv_path: str):
    if not os.path.exists(csv_path):
        return pd.DataFrame()
    
    # 读取表格
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    # 关键列名
    well_col = '统一编号'
    year_col = '年份'

    # 自动定位“地面高程”列 -> 数值
    elev_candidates = [c for c in df.columns if re.search(r'地面高程', str(c))]
    if not elev_candidates:
        raise ValueError("在CSV中找不到包含“地面高程”的列, 请检查列名。")
    elev_col = elev_candidates[0]
    df[elev_col] = df[elev_col].astype(str).str.extract(r'([-+]?\d*\.?\d+)')[0]
    df[elev_col] = pd.to_numeric(df[elev_col], errors='coerce')

    # 监测日列
    pattern = re.compile(r'^M\d{2}_D\d{2}$')
    day_cols = [c for c in df.columns if pattern.match(str(c))]
    if not day_cols:
        raise ValueError("未找到形如 Mxx_Dxx 的监测日列。")

    # melt成长表
    df_long = df.melt(
        id_vars=[well_col, year_col],
        value_vars=day_cols,
        var_name='观测日期',
        value_name='gw_level_m'
    )

    # 解析日期
    md = df_long['观测日期'].str.extract(r'M(\d{2})_D(\d{2})').astype(float)
    df_long['month'] = md[0]
    df_long['day']   = md[1]
    df_long[year_col] = pd.to_numeric(df_long[year_col], errors='coerce')
    df_long = df_long.dropna(subset=[year_col, 'month', 'day'])

    df_long['date'] = pd.to_datetime(
        df_long[year_col].astype(int).astype(str) + '-' +
        df_long['month'].astype(int).astype(str).str.zfill(2) + '-' +
        df_long['day'].astype(int).astype(str).str.zfill(2),
        errors='coerce'
    )

    # 数值清洗
    df_long['gw_level_m'] = pd.to_numeric(df_long['gw_level_m'], errors='coerce')
    df_long = df_long.dropna(subset=['date', 'gw_level_m'])

    # 统一列名
    df_long = df_long.rename(columns={well_col: '统一编号'})
    return df_long[['统一编号', 'date', 'gw_level_m']]

# ============ 5) 主流程 ============
def main():
    warnings.filterwarnings("ignore", category=UserWarning)

    _ensure_dirs(OUT_DIR)

    # Step A：得到 coords_df
    coords_df = build_coords_from_big_csv_simple(IN_CSV, COORDS_OUT)
    
    # 从 coords_df 中构建 “统一编号 -> 高程(m)” 的映射
    id_to_elev = {}
    if 'elevation_m' in coords_df.columns:
        tmp = coords_df[['id', 'elevation_m']].dropna()
        # 转为字典，key/val 都转成合适类型
        id_to_elev = {str(r['id']): float(r['elevation_m']) for _, r in tmp.iterrows()}

    if not os.path.exists(IN_CSV):
        print("找不到原始CSV：", IN_CSV); return

    # 扫描 H5 元数据
    h5_files = sorted(glob.glob(os.path.join(DATA_DIR, H5_PATTERN)))
    if not h5_files:
        print("未在数据目录发现 H5：", DATA_DIR); return

    metas: List[Dict[str, Any]] = []
    print(f"发现 {len(h5_files)} 个 H5，读取元数据……")
    for p in h5_files:
        try:
            meta_one = scan_vu_meta(p)
            metas.append(meta_one)
            if VERBOSE:
                print(f"  + {meta_one['base']}: "
                    f"lon[{meta_one['lon_min']:.5f},{meta_one['lon_max']:.5f}] "
                    f"lat[{meta_one['lat_min']:.5f},{meta_one['lat_max']:.5f}] "
                    f"shape={meta_one['vu_shape']} t_ax={meta_one['t_ax']}")
        except Exception as e:
            print(f"  × {os.path.basename(p)} — {type(e).__name__}: {e}")

    if not metas:
        print("没有可用的 H5 元数据，退出。"); return

    # （旧的每H5缓存留存但未使用，不影响）
    merged_by_h5: Dict[str, List[pd.DataFrame]] = {m["base"]: [] for m in metas}

    # ====== A/D Frame Pairs ======
    FRAME_PAIRS = [
        ('128A_05172','033D_05106'),
        ('055A_05021','135D_05023'),
        ('055A_05221','135D_05222'),
    ]
    def _which_pair_and_side(base: str):
        for a, d in FRAME_PAIRS:
            if base.startswith(a): return f"{a}__{d}", 'A'
            if base.startswith(d): return f"{a}__{d}", 'D'
        return None, None

    # —— 收集每个统一编号在所有 H5 的时间序列（按“配对”归集）
    per_id_pair: Dict[str, Dict[str, Dict[str, List[pd.DataFrame]]]] = {}
    print(f"开始提取（共 {len(coords_df)} 个坐标点 × {len(metas)} 个 H5 ）……")

    for i, row in coords_df.iterrows():
        ident = row['id']
        lon = float(row['lon'])
        lat = float(row['lat'])

        for meta in metas:
            pair_key, side = _which_pair_and_side(meta['base'])
            if pair_key is None or side not in ('A', 'D'):
                continue

            if not (meta['lon_min'] <= lon <= meta['lon_max'] and meta['lat_min'] <= lat <= meta['lat_max']):
                continue
            
            try:
                df_ts, _ = extract_and_plot(meta, lon, lat, ident, OUT_DIR, figsize=FIGSIZE, dpi=DPI, do_plot_single=False)
                if df_ts is not None and not df_ts.empty:
                    per_id_pair.setdefault(ident, {}).setdefault(pair_key, {}).setdefault(side, []).append(df_ts)
            except Exception:
                pass

    PALETTE = {'A': 'steelblue', 'D': 'darkorange'}
    EDGE    = {'A': 'navy',      'D': 'saddlebrown'}

    tasks = []
    summary_rows = []  # collect slopes for global scatter later
    for ident, pairs in per_id_pair.items():
        for pair_key, sides in pairs.items():
            if ('A' in sides and sides['A']) and ('D' in sides and sides['D']):
                tasks.append((ident, pair_key, sides))
    if VERBOSE:
        print(f"将绘制 {len(tasks)} 张配对图……")

    gw_all = _load_groundwater_long(IN_CSV)

    count_plots = 0
    for ident, pair_key, sides in tqdm(tasks, desc="Plotting A&D pairs", unit="fig", ncols=100, dynamic_ncols=True):

            fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)   # 左轴（地下水）
            ax2 = ax.twinx()                                   # 右轴（A/D）

            # —— 建两个列表，收集“主数据”范围建议
            zoom_ranges_left  = []
            zoom_ranges_right = []

            # Prepare containers for slopes/uncertainties used for summary-only CSV + scatter
            gw_slope = None; gw_unc = None
            a_slope = None;  a_unc = None
            d_slope = None;  d_unc = None

            # Groundwater (左轴)
            if gw_all is not None and not gw_all.empty:
                df_gw = gw_all[gw_all['统一编号'].astype(str) == str(ident)].copy()
                if not df_gw.empty:
                    df_gw = df_gw.sort_values('date')

                    # plot
                    sns.scatterplot(
                        x=df_gw['date'], y=df_gw['gw_level_m'], ax=ax,
                        s=50, alpha=0.5, facecolor='grey', edgecolor='dimgray', linewidth=0.8,
                        label='Groundwater', legend=False
                    )

                    # WLS + outlier
                    if pd.to_numeric(df_gw['gw_level_m'], errors='coerce').notna().sum() >= 3:
                        fit_gw = _wls_two_pass(df_gw, x_col='date', y_col='gw_level_m')
                        if fit_gw is not None:
                            ax.plot(fit_gw['x'], fit_gw['fitted'], '-', linewidth=1.8,
                                    color='black', label='GW WLS')
                            r = _plot_outliers_and_get_range(ax, fit_gw, color='maroon', label='GW Outlier')
                            if r: zoom_ranges_left.append(r)
                            # record GW slope and uncertainty (m/yr)
                            try:
                                gw_slope = float(fit_gw.get('slope', float('nan')))
                            except Exception:
                                gw_slope = None
                            try:
                                gw_unc = float(fit_gw.get('slope_stderr', float('nan')))
                            except Exception:
                                gw_unc = None

            # A 侧 (右轴)
            for df_ts in sides.get('A', []):
                df = df_ts.sort_values('date')
                sns.scatterplot(
                    x=df['date'], y=df['displacement'], ax=ax2,
                    s=50, alpha=0.5, facecolor=PALETTE['A'], edgecolor=EDGE['A'], linewidth=0.8,
                    label=df['h5'].iloc[0] if 'h5' in df.columns and not df.empty else 'A'
                )
                fit = _wls_two_pass(df, x_col='date', y_col='displacement')
                if fit is not None:
                    ax2.plot(fit['x'], fit['fitted'], '-', linewidth=1.8, color=PALETTE['A'], label='A WLS')
                    r = _plot_outliers_and_get_range(ax2, fit, color='red', label='A Outlier')
                    if r: zoom_ranges_right.append(r)

            # D 侧 (右轴)
            for df_ts in sides.get('D', []):
                df = df_ts.sort_values('date')
                sns.scatterplot(
                    x=df['date'], y=df['displacement'], ax=ax2,
                    s=50, alpha=0.5, facecolor=PALETTE['D'], edgecolor=EDGE['D'], linewidth=0.8,
                    label=df['h5'].iloc[0] if 'h5' in df.columns and not df.empty else 'D'
                )
                fit = _wls_two_pass(df, x_col='date', y_col='displacement')
                if fit is not None:
                    ax2.plot(fit['x'], fit['fitted'], '-', linewidth=1.8, color=PALETTE['D'], label='D WLS')
                    r = _plot_outliers_and_get_range(ax2, fit, color='red', label='D Outlier')
                    if r: zoom_ranges_right.append(r)

            # Axis & styles
            ax.set_title(f'ID: {ident} — Pair: {pair_key}', fontsize=12)
            ax.set_xlabel('Date', fontsize=12)
            ax.set_ylabel('Ground water level (m)', fontsize=12)
            ax2.set_ylabel('Displacement (mm/year)', fontsize=12)
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
            ax.grid(True, linestyle='--', alpha=0.5)

            # 对左右y轴都应用自缩放
            _apply_axis_zoom(ax,  zoom_ranges_left)
            _apply_axis_zoom(ax2, zoom_ranges_right)

            # y轴取消科学计数法，保留两位小数
            ax.ticklabel_format(style='plain', axis='y', useOffset=False)
            ax.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.2f'))

            # legend
            for a in (ax, ax2):
                leg = a.get_legend()
                if leg is not None:
                    leg.remove()
            h1, l1 = ax.get_legend_handles_labels()
            h2, l2 = ax2.get_legend_handles_labels()
            H = (h1 or []) + (h2 or [])
            L = (l1 or []) + (l2 or [])
            if H and L:
                ax2.legend(H, L, loc='upper right', frameon=False, fontsize=9)

            elev_str = ""
            if ident in id_to_elev:
                elev_str = f"Elev: {id_to_elev[ident]:.2f} m"

            # —— 计算三组斜率（用于注记）
            gw_slope = None  # m/year
            if gw_all is not None and not gw_all.empty:
                df_gw = gw_all[gw_all['统一编号'].astype(str) == str(ident)].sort_values('date').copy()
                y_col_gw = 'gw_level_m' if 'gw_level_m' in df_gw.columns else ('水位' if '水位' in df_gw.columns else None)
                if y_col_gw and df_gw[y_col_gw].notna().sum() >= 3:
                    fit_gw_for_text = _wls_two_pass(df_gw, x_col='date', y_col=y_col_gw)
                    if fit_gw_for_text is not None:
                        gw_slope = float(fit_gw_for_text['slope'])  # m/yr

            # A/D 合并后各做一次综合 WLS（mm/year）
            # Combined A/D slope using all A or all D time series (mm/yr)
            if sides.get('A'):
                try:
                    dfA_all = pd.concat(sides['A'], ignore_index=True).sort_values('date')
                    fitA_all = _wls_two_pass(dfA_all, x_col='date', y_col='displacement')
                    if fitA_all is not None:
                        a_slope = float(fitA_all['slope'])  # mm/yr
                        try:
                            a_unc = float(fitA_all.get('slope_stderr', float('nan')))
                        except Exception:
                            a_unc = None
                except Exception:
                    pass

            if sides.get('D'):
                try:
                    dfD_all = pd.concat(sides['D'], ignore_index=True).sort_values('date')
                    fitD_all = _wls_two_pass(dfD_all, x_col='date', y_col='displacement')
                    if fitD_all is not None:
                        d_slope = float(fitD_all['slope'])
                        try:
                            d_unc = float(fitD_all.get('slope_stderr', float('nan')))
                        except Exception:
                            d_unc = None
                except Exception:
                    pass

            # —— 组合注记文本
            lines = []
            if ident in id_to_elev:
                lines.append(f"Elev: {id_to_elev[ident]:.2f} m")
            if gw_slope is not None:
                lines.append(f"GW slope: {gw_slope:.3f} m/yr")
            if a_slope is not None:
                lines.append(f"A slope:  {a_slope:.2f} mm/yr")
            if d_slope is not None:
                lines.append(f"D slope:  {d_slope:.2f} mm/yr")

            if lines:
                ax.text(
                    0.02, 0.02, "\n".join(lines),
                    transform=ax.transAxes, ha='left', va='bottom', fontsize=9,
                    bbox=dict(facecolor='white', alpha=0.65, edgecolor='none', boxstyle='round,pad=0.3')
                )

            plt.tight_layout()
            out_png = os.path.join(OUT_DIR, f"{_safe_name(ident)}__{_safe_name(pair_key)}.png")
            # Accumulate for global scatter only (no per-plot CSV)
            try:
                summary_rows.append({
                    'gw_slope': gw_slope,
                    'gw_uncertainty': gw_unc,
                    'A_slope': a_slope,
                    'A_uncertainty': a_unc,
                    'D_slope': d_slope,
                    'D_uncertainty': d_unc,
                })
            except Exception:
                pass
            plt.savefig(out_png, dpi=DPI); plt.close(fig)
            count_plots += 1

            if VERBOSE:
                print (f"  ✓ 图：{out_png}")

    # ---- Summary CSV + two scatter plots (A vs GW, D vs GW) ----
    try:
        import pandas as _pd
        import matplotlib.pyplot as _plt
        import seaborn as _sns
        if summary_rows:
            df_summary = _pd.DataFrame(summary_rows)
            # 保留至少有 GW 斜率的行
            df_summary = df_summary.dropna(subset=['gw_slope'])
            summary_csv = os.path.join(OUT_DIR, 'pair_slopes_summary.csv')
            df_summary.to_csv(summary_csv, index=False)

            # 1) A vs GW
            fig, ax = _plt.subplots(figsize=(6,5))
            _sns.scatterplot(data=df_summary, x='gw_slope', y='A_slope', ax=ax)
            try:
                ax.errorbar(df_summary['gw_slope'], df_summary['A_slope'],
                            xerr=df_summary['gw_uncertainty'], yerr=df_summary['A_uncertainty'],
                            fmt='none', ecolor='gray', alpha=0.6, capsize=2)
            except Exception:
                pass
            ax.set_xlabel('GW level slope (m/yr)')
            ax.set_ylabel('A slope (mm/yr)')
            _plt.tight_layout()
            _plt.savefig(os.path.join(OUT_DIR, 'scatter_A_vs_gw.png'), dpi=300)
            _plt.close(fig)

            # 2) D vs GW
            fig, ax = _plt.subplots(figsize=(6,5))
            _sns.scatterplot(data=df_summary, x='gw_slope', y='D_slope', ax=ax)
            try:
                ax.errorbar(df_summary['gw_slope'], df_summary['D_slope'],
                            xerr=df_summary['gw_uncertainty'], yerr=df_summary['D_uncertainty'],
                            fmt='none', ecolor='gray', alpha=0.6, capsize=2)
            except Exception:
                pass
            ax.set_xlabel('GW level slope (m/yr)')
            ax.set_ylabel('D slope (mm/yr)')
            _plt.tight_layout()
            _plt.savefig(os.path.join(OUT_DIR, 'scatter_D_vs_gw.png'), dpi=300)
            _plt.close(fig)
    except Exception:
        pass

    print('全部完成。')

if __name__ == "__main__":
    main()
