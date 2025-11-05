#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import glob
import warnings
import numpy as np
import pandas as pd
import h5py
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from decimal import Decimal, InvalidOperation, localcontext

# ============ 0) 路径 & 参数 ============
IN_CSV = '/Users/lianglu/Desktop/GOBI/data/2018-2022石羊河监测井数据_水位.csv'
OUT_DIR = '/Users/lianglu/Desktop/GOBI/Outputs/wls_ts'
DATA_DIR = '/Users/lianglu/Desktop/GOBI/data'
H5_PATTERN = "*.h5"
COORDS_OUT = os.path.join(OUT_DIR, 'coords_for_ts.csv')
os.makedirs(OUT_DIR, exist_ok=True)

# observation有效性
YEAR_MIN = 2014
YEAR_MAX = 2023
START_DATE = pd.Timestamp(f"{YEAR_MIN}-01-01")
END_DATE   = pd.Timestamp(f"{YEAR_MAX}-12-31")

# 图形风格
FIGSIZE = (12, 7)
DPI = 180

# ============ 1) plot theme ============
sns.set_theme(style="whitegrid", context="talk")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']

# ============ 2) functions ============
def _safe_name(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', '_', str(s))

def _ensure_dirs(*paths):
    for p in paths:
        os.makedirs(p, exist_ok=True)

# def _find_col(cols, candidates):
#     low = {c.lower(): c for c in cols}
#     for cand in candidates:
#         k = str(cand).lower()
#         if k in low:
#             return low[k]
#     return None
# 
# def _coerce_float(series):
#     return pd.to_numeric(series.astype(str).str.strip(), errors="coerce")
# 
# def _in_range_lon_lat(lon, lat):
#     return np.isfinite(lon) & np.isfinite(lat) & (lon >= -180) & (lon <= 180) & (lat >= -90) & (lat <= 90)

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
                # 判断是否为整数
                if d == d.to_integral_value():
                    # 量化到整数，转成无指数字符串
                    return format(d.quantize(Decimal(1)), "f")
                else:
                    # 保留为小数，转 'f' 并去掉末尾 0 和小数点
                    out = format(d.normalize(), "f")
                    if "." in out:
                        out = out.rstrip("0").rstrip(".")
                    return out
        except InvalidOperation:
            # 不是纯数字/科学计数，原样返回
            return txt
    return s.apply(_one)

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

    # 标准化列名（去首尾空格）
    df.columns = [str(c).strip() for c in df.columns]

    # 必需列检查
    miss = [c for c in (id_col, lon_col, lat_col) if c not in df.columns]
    if miss:
        # 打印前若干列帮助定位
        sample_cols = list(df.columns)[:20]
        raise KeyError(f'缺少必需列：{miss}；CSV 实际列名前20个：{sample_cols}')

    sub = df[[id_col, lon_col, lat_col]].copy()
    sub.columns = ['id', 'lon', 'lat']

    # 统一编号去科学计数法 & 保持精度
    before = sub['id'].copy()
    sub['id'] = normalize_id_series(sub['id'])

    # 清洗为数值（去全角空格/中文空格/杂字符）
    def _to_num(s):
        s = s.astype(str).str.replace('\u3000', ' ', regex=False).str.strip()
        return pd.to_numeric(s, errors='coerce')
    sub['lon'] = _to_num(sub['lon'])
    sub['lat'] = _to_num(sub['lat'])

    # 合理范围过滤
    m = sub['lon'].between(-180, 180) & sub['lat'].between(-90, 90)
    sub = sub[m & sub['lon'].notna() & sub['lat'].notna()]

    if sub.empty:
        raise ValueError('三列已读取，但没有通过经纬度清洗/范围过滤的有效行。请检查经纬度格式（是否为小数度）。')

    # 按统一编号去重（如果一个编号对应多坐标，只保留第一条）
    sub = sub.drop_duplicates(subset=['id'], keep='first').reset_index(drop=True)

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    sub.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f'[Step A] 已保存坐标清单：{out_csv} （{len(sub)} 行）')
    return sub

# ============ 4) Step B: 扫描 H5 数据，提取并作图 ============
def scan_h5_meta(h5_path: str) -> Dict[str, Any]:
    base = os.path.basename(h5_path)
    with h5py.File(h5_path, "r") as f:
        corner_lon = _get_scalar(f, ["corner_lon"])
        post_lon   = _get_scalar(f, ["post_lon"])
        corner_lat = _get_scalar(f, ["corner_lat"])
        post_lat   = _get_scalar(f, ["post_lat"])
        cum_path   = _find_ds_path(f, ["cum"])
        if not cum_path:
            raise KeyError(f"{base}: 'cum' dataset not found")
        dates_path = _find_ds_path(f, ["imdates","dates","date"])
        cum_shape  = tuple(_read_ds(f, cum_path).shape)
        ntime      = int(np.size(_read_ds(f, dates_path))) if dates_path else None
        t_ax       = _find_time_axis(cum_shape, ntime)

        if t_ax == 0: ny, nx = cum_shape[1], cum_shape[2]
        elif t_ax == 1: ny, nx = cum_shape[0], cum_shape[2]
        else: ny, nx = cum_shape[0], cum_shape[1]

        lon_min, lon_max = _extent_from_corner_post(corner_lon, post_lon, nx)
        lat_min, lat_max = _extent_from_corner_post(corner_lat, post_lat, ny)

    return dict(
        path=h5_path, base=base,
        cum_path=cum_path, dates_path=dates_path,
        cum_shape=cum_shape, t_ax=t_ax, ntime=ntime,
        nx=nx, ny=ny,
        corner_lon=corner_lon, post_lon=post_lon,
        corner_lat=corner_lat, post_lat=post_lat,
        lon_min=lon_min, lon_max=lon_max,
        lat_min=lat_min, lat_max=lat_max
    )

def extract_and_plot(meta: Dict[str, Any], lon: float, lat: float, ident: Optional[str],
                     out_root: str, figsize=(12,7), dpi=180):
    """
    两道判定：
      1) 空间范围：在 main() 里先判（不在范围跳过）
      2) 时间与观测：日期可解析且在 [YEAR_MIN, YEAR_MAX] 之间有 ≥1 个有效观测
    只有通过②才会画图并返回 df_ts；否则返回 (None, None)。
    """
    with h5py.File(meta["path"], "r") as f:
        cum   = _read_ds(f, meta["cum_path"])
        dates = _read_ds(f, meta["dates_path"]) if meta["dates_path"] else np.arange(meta["cum_shape"][meta["t_ax"]])

        # 像元定位
        ix = _clamp_to_pixel(meta["corner_lon"], meta["post_lon"], lon, meta["nx"])
        iy = _clamp_to_pixel(meta["corner_lat"], meta["post_lat"], lat, meta["ny"])
        lon_pix = meta["corner_lon"] + ix * meta["post_lon"]
        lat_pix = meta["corner_lat"] + iy * meta["post_lat"]

        # 时序切片
        if meta["t_ax"] == 0: ts = cum[:, iy, ix]
        elif meta["t_ax"] == 1: ts = cum[iy, :, ix]
        else: ts = cum[iy, ix, :]

        # 日期解析
        dt = _dates_to_datetime(dates)
        dt = pd.to_datetime(dt)

    # —— 判定②：有“位移为有限数 & 日期非NaT & 日期在窗口内”的观测
    dt_s = pd.Series(dt)
    ok = np.isfinite(ts) & dt_s.notna() & dt_s.between(START_DATE, END_DATE, inclusive="both")
    if not np.any(ok):
        return None, None  # 不画图、不合并

    # —— 合并用的长表（只保留有效观测）
    df_ts = pd.DataFrame({
        "id":  ident if ident is not None else "",
        "lon": float(lon),
        "lat": float(lat),
        "date": pd.to_datetime(dt_s[ok].values),
        "displacement": np.array(ts)[ok],
        "h5": meta["base"],
        "ix": int(ix),
        "iy": int(iy),
        "pix_lon": float(lon_pix),
        "pix_lat": float(lat_pix),
    })


    # —— 保存散点图（标题精简，Y轴在右）
    h5_dir   = os.path.join(out_root, meta["base"])
    plot_dir = os.path.join(h5_dir, "plots")
    _ensure_dirs(plot_dir)
    tag = f"{_safe_name(ident) + '__' if ident else ''}{os.path.splitext(meta['base'])[0]}"
    out_png = os.path.join(plot_dir, f"{_safe_name(tag)}.png")

    fig, ax = plt.subplots(figsize=figsize)
    sns.scatterplot(
        x=df_ts["date"], y=df_ts["displacement"], ax=ax,
        s=60, alpha=0.65, facecolor='steelblue', edgecolor='navy', linewidth=0.8
    )

    # 时间轴
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_minor_formatter(plt.NullFormatter())

    # Y 轴放右侧
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(True)

    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Displacement (mm/year)', fontsize=12)

    title = f"Well Code: {ident if ident is not None else ''}, Lon&Lat: ({lon:.5f}, {lat:.5f}), Frame: {meta['base']}"
    ax.set_title(title, fontsize=12)

    ax.grid(True, which='major', linestyle='--', linewidth=0.7, color='grey')
    ax.grid(True, which='minor', linestyle='--', linewidth=0.5, color='lightgrey')
    ax.tick_params(axis='both', labelsize=12)
    plt.tight_layout()
    plt.savefig(out_png, dpi=dpi)
    plt.close(fig)

    return df_ts, out_png

# ============ 5) 主流程 ============
def main():
    warnings.filterwarnings("ignore", category=UserWarning)

    # 输出与日志
    _ensure_dirs(OUT_DIR)
    log_dir = os.path.join(OUT_DIR, "logs"); _ensure_dirs(log_dir)
    log_path = os.path.join(log_dir, "run_log.csv")
    if os.path.exists(log_path):
        os.remove(log_path)
    with open(log_path, "w", encoding="utf-8") as fw:
        fw.write("row_index,id,lon,lat,h5,in_extent,png_path,status,message\n")

    # Step A：得到 coords_df
    if not os.path.exists(IN_CSV):
        print("找不到原始CSV：", IN_CSV); return
    coords_df = build_coords_from_big_csv_simple(IN_CSV, COORDS_OUT)

    # 扫描 H5 元数据
    h5_files = sorted(glob.glob(os.path.join(DATA_DIR, H5_PATTERN)))
    if not h5_files:
        print("未在数据目录发现 H5：", DATA_DIR); return

    metas: List[Dict[str, Any]] = []
    print(f"发现 {len(h5_files)} 个 H5，读取元数据……")
    for p in h5_files:
        try:
            m = scan_h5_meta(p)
            metas.append(m)
            print(f"  + {m['base']}: lon[{m['lon_min']:.5f},{m['lon_max']:.5f}] lat[{m['lat_min']:.5f},{m['lat_max']:.5f}] shape={m['cum_shape']} t_ax={m['t_ax']}")
        except Exception as e:
            print(f"  × {os.path.basename(p)} — {e}")

    if not metas:
        print("没有可用的 H5 元数据，退出。"); return

    # 为“每个 h5”准备合并缓存（长表片段；最终会 pivot 成宽表）
    merged_by_h5: Dict[str, List[pd.DataFrame]] = {m["base"]: [] for m in metas}

    print(f"开始提取（共 {len(coords_df)} 个坐标点）……")
    for i, row in coords_df.iterrows():
        lon = float(row["lon"]); lat = float(row["lat"])
        ident = str(row["id"]) if "id" in coords_df.columns else None

        for meta in metas:
            # —— 判定①：空间范围
            in_lon = _in_extent(lon, meta["lon_min"], meta["lon_max"])
            in_lat = _in_extent(lat, meta["lat_min"], meta["lat_max"])
            if not (in_lon and in_lat):
                with open(log_path, "a", encoding="utf-8") as fw:
                    fw.write(f"{i},{ident or ''},{lon},{lat},{meta['base']},NO,,SKIP,Outside extent\n")
                continue

            # 命中范围（打印一句）
            # print(f"（{lon:.5f}，{lat:.5f} 在 {meta['base']} 范围内）")

            # —— 判定② + 作图
            try:
                df_ts, png_path = extract_and_plot(meta, lon, lat, ident, OUT_DIR, figsize=FIGSIZE, dpi=DPI)
                if df_ts is None:
                    print(f"（{lon:.5f}，{lat:.5f} 在 {meta['base']} 内没有有效数据）")
                    with open(log_path, "a", encoding="utf-8") as fw:
                        fw.write(f"{i},{ident or ''},{lon},{lat},{meta['base']},YES,,SKIP,NO_OBS\n")
                    continue

                # 两道判定都通过：并入合并缓存 & 日志 OK
                merged_by_h5[meta["base"]].append(df_ts)
                with open(log_path, "a", encoding="utf-8") as fw:
                    fw.write(f"{i},{ident or ''},{lon},{lat},{meta['base']},YES,{png_path},OK,\n")
            except Exception as e_hit:
                with open(log_path, "a", encoding="utf-8") as fw:
                    fw.write(f"{i},{ident or ''},{lon},{lat},{meta['base']},YES,,FAIL,{repr(e_hit)}\n")
                print(f"  × row {i} @ {meta['base']} — {e_hit}")

    # 每个 H5 汇总生成csv
    total_valid = 0  # <--- 新增：统计总数
    for meta in metas:
        base = meta["base"]
        parts = merged_by_h5[base]

        if not parts:
            # 没有任何有效观测
            print(f"[Summary] {base}: 有效经纬度 0 个")
            continue

        big_long = pd.concat(parts, ignore_index=True)

        # 只用有效观测
        big_long = big_long[pd.notna(big_long["date"]) & np.isfinite(big_long["displacement"])]

        # csv：index = (id, lon, lat)，columns = 日期(YYYY-MM-DD)，values = displacement
        big_long["date_str"] = pd.to_datetime(big_long["date"]).dt.strftime("%Y-%m-%d")
        wide = big_long.pivot_table(index=["id","lon","lat"], columns="date_str",
                                    values="displacement", aggfunc="first")

        # 日期列排序
        wide = wide.reindex(sorted(wide.columns), axis=1)

        # debug 汇总
        count_ids = wide.shape[0]
        print(f"[Summary] {base}: 有效经纬度 {count_ids} 个")
        total_valid += count_ids

        # 落盘
        h5_dir  = os.path.join(OUT_DIR, base)
        csv_dir = os.path.join(h5_dir); _ensure_dirs(csv_dir)
        out_csv = os.path.join(csv_dir, f"{os.path.splitext(base)[0]}__ALL_POINTS_WIDE.csv")
        wide.reset_index().to_csv(out_csv, index=False, encoding="utf-8-sig")
        print(f"  ✓ CSV：{out_csv}  （{wide.shape[0]} 行 × {wide.shape[1]-3} 日期列）")

    print("\n全部完成。")
    print("坐标清单：", COORDS_OUT)
    print("运行日志：", log_path)
    print("图 & CSV：", OUT_DIR)

if __name__ == "__main__":
    main()
