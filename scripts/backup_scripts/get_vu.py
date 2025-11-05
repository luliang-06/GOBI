#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from typing import Optional, Tuple, List
import numpy as np
import h5py
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')

FILE_SUFFIX = '.cum_filt.h5'

def read_cum_array(cum_h5_path: str) -> np.ndarray:

    print(f'[Read] Loading hdf5 files: {cum_h5_path}')

    with h5py.File(cum_h5_path, 'r') as f:
        if 'cum' not in f:
            raise ValueError(f'{os.path.basename(cum_h5_path)} does not contain cum array.')
        dset = f['cum']
        if dset.ndim != 3:
            raise ValueError(f"'cum' is not 3d rray, got ndim={dset.ndim}")
        
        print(f'[Read] hdf5 shape={dset.shape} dtype={dset.dtype}')

        arr = dset[:]
    return arr


def read_geoU(geoU_path: str) -> Tuple[np.ndarray, dict, tuple, rasterio.Affine, str]:

    print(f'[Read] Loading geo.U tif: {geoU_path}')

    with rasterio.open(geoU_path) as src:
        arr = src.read(1)
        profile = src.profile
        bounds = src.bounds
        transform = src.transform
        crs = src.crs

        print(f'[Read] geo.U shape={arr.shape} dtype={arr.dtype}')

    return arr, profile, bounds, transform, crs


def resample_geoU_to(geoU_path: str, target_h: int, target_w: int) -> Tuple[np.ndarray, dict]:
    """把 geo.U 重采样到 (target_h, target_w)（保持原始边界和 CRS）。"""
    with rasterio.open(geoU_path) as src:
        src_arr = src.read(1)
        src_transform = src.transform
        src_crs = src.crs
        left, bottom, right, top = src.bounds

        dst_arr = np.empty((target_h, target_w), dtype=np.float32)
        dst_transform = from_bounds(left, bottom, right, top, width=target_w, height=target_h)

        reproject(
            source=src_arr,
            destination=dst_arr,
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=src_crs,
            resampling=Resampling.bilinear
        )

        dst_profile = src.profile.copy()
        dst_profile.update(
            height=target_h,
            width=target_w,
            transform=dst_transform,
            dtype=rasterio.float32
        )
        return dst_arr, dst_profile
    

def divide(cum_THW: np.ndarray, geoU_HW: np.ndarray) -> np.ndarray:
    T, H, W = cum_THW.shape
    if geoU_HW.shape != (H, W):
        raise ValueError(f'geo.U shape {geoU_HW.shape} != cum spatial {(H, W)}')
    
    print('[Divide] 3D (T,H,W) stack detected, broadcasting over time...')

    geoU_b = geoU_HW[None, :, :]
    
    with np.errstate(divide='ignore', invalid='ignore'):
        out = (cum_THW.astype(np.float32) / geoU_b.astype(np.float32))
    
    invalid = ~np.isfinite(cum_THW) | ~np.isfinite(geoU_b) | (geoU_b == 0)
    out[invalid] = np.nan

    valid_count = out.size - np.count_nonzero(np.isnan(out))

    print(f'[Divide] valid voxels: {valid_count}/{out.size} (shape={out.shape})')

    return out


def write_vu_tif(vu: np.array, tif_profile: dict, out_tif: str) -> None:
    prof = tif_profile.copy()
    prof.update(dtype=rasterio.float32, count=1, compress='deflate', predictor=2)

    print(f'[Write] {out_tif}')

    with rasterio.open(out_tif, 'w', **prof) as dst:
        dst.write(vu, 1)


def write_vu_h5(vu: np.ndarray, cum_h5_path: str, out_hdf5: str) -> None:
    print(f'[Write] {out_hdf5}')

    with h5py.File(out_hdf5, 'w') as f_out:
        d = f_out.create_dataset('vu', data=vu, compression='gzip', compression_opts=4, shuffle=True)
        d.attrs['description'] = 'vertical cumulative displacement'
        d.attrs['units'] = 'same_as_cum_input'
        d.attrs['source'] = os.path.basename(cum_h5_path)

        try:
            with h5py.File(cum_h5_path, 'r') as f_in:
                if 'imdates' in f_in:
                    f_out.create_dataset('imdates', data=f_in['imdates'][:], compression='gzip', 
                                         compression_opts=4, shuffle=True)
                
                have_lonlat = ('lon' in f_in) and ('lat' in f_in) 
                need = ['corner_lon', 'corner_lat', 'post_lon', 'post_lat']
                if all(k in f_in for k in need):
                    corner_lon = float(f_in['corner_lon'][()])
                    corner_lat = float(f_in['corner_lat'][()])
                    post_lon   = float(f_in['post_lon'][()])
                    post_lat   = float(f_in['post_lat'][()])

                    if vu.ndim != 3:
                        raise ValueError("vu must be 3D (T,H,W) to rebuild lon/lat")
                    _, H, W = vu.shape

                    x = corner_lon + np.arange(W, dtype=np.float64) * post_lon
                    y = corner_lat + np.arange(H, dtype=np.float64) * post_lat
                    lon = np.broadcast_to(x[None, :], (H, W))
                    lat = np.broadcast_to(y[:, None], (H, W))

                    f_out.create_dataset('lon', data=lon, compression='gzip', compression_opts=4, shuffle=True)
                    f_out.create_dataset('lat', data=lat, compression='gzip', compression_opts=4, shuffle=True)

                    f_out.create_dataset('corner_lon', data=corner_lon)
                    f_out.create_dataset('corner_lat', data=corner_lat)
                    f_out.create_dataset('post_lon',   data=post_lon)
                    f_out.create_dataset('post_lat',   data=post_lat)
                
                else:
                    print('[Warning] 源H5无 lon/lat 且缺少 corner*/post*，无法重建 lon/lat。')
            
            if 'metadata' in f_in and isinstance(f_in['metadata'], h5py.Group):
                grp_in = f_in['metadata']
                grp_out = f_out.create_group('metadata')
                for k, v in grp_in.attrs.items():
                    grp_out.attrs[k] = v
        
        except Exception as e:
            print(f'[Warning] 复制/重建元数据失败：{e}')



def guess_geoU_path_for_base(dirpath: str, base: str) -> Optional[str]:
    strict = os.path.join(dirpath, f"{base}.geo.U.tif")
    if os.path.exists(strict):
        return strict
    for fn in os.listdir(dirpath):
        lfn = fn.lower()

        if lfn.endswith('.tif') and 'geo.u' in lfn and base.lower() in lfn:
            return os.path.join(dirpath, fn)
    
    return None  


def collect_pairs(root: str) -> List[Tuple[str, str, str]]:
    pairs = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(FILE_SUFFIX):
                cum_path = os.path.join(dirpath, fn)
                base = fn[:-len(FILE_SUFFIX)]
                geoU_path = guess_geoU_path_for_base(dirpath, base)
                if geoU_path:
                    pairs.append((cum_path, geoU_path, base))
                else:
                    print(f"[Pairing] Cannot find paired geo.U.tif  ({dirpath}, base={base})")
    
    print(f"[Summary] Available pairs: {len(pairs)}")

    return pairs


def process_one_pair(cum_h5: str, geoU_tif: str, base: str) -> None:
    
    print("="*80)
    print(f"[Processing] base={base}")
    
    cum = read_cum_array(cum_h5)
    T, H, W = cum.shape[0], cum.shape[1], cum.shape[2]
    geoU, profile, bounds, transform, crs = read_geoU(geoU_tif)

    if geoU.shape != (H, W):
        print(f"[Resample] geo.U {geoU.shape} -> {(H, W)} to match cum spatial")
        geoU, profile = resample_geoU_to(geoU_tif, target_h=H, target_w=W)

    vu = divide(cum, geoU)

    vu_for_tif = vu[-1, :, :]
    out_tif = os.path.join(os.path.dirname(cum_h5), f"{base}.filt_vu.tif")
    out_h5  = os.path.join(os.path.dirname(cum_h5), f"{base}.filt_vu.h5")
    
    write_vu_tif(vu_for_tif, profile, out_tif)
    write_vu_h5(vu, cum_h5, out_h5)
    
    print(f"[Finish] Outputs: \n  - {out_tif}\n  - {out_h5}")


def main():
    root = DATA_DIR
    print(f"[Start] Scaning: {root}")

    pairs = collect_pairs(root)
    if not pairs:
        print("[End] Can not fond pairs")
        sys.exit(0)

    for cum_h5, geoU_tif, base in pairs:
        try:
            process_one_pair(cum_h5, geoU_tif, base)
        except Exception as e:
            print(f"[Error] base={base} Process failed: {e}")

    print("[Done] ✅")


if __name__ == '__main__':
    main()