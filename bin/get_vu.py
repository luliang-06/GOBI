#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Written by Lu Liang, University of Edinburgh, School of Geosciences, 2025.

===========
Description
===========
This script do the division between 'cum' and 'U.geo' of input hdf5 files to get vertical cum displacement.
The results of division ('cumU' & 'velU') will be stored in the same hdf5 file imported.

============
Inputs Files
============
data/
    *.cum_filt_deramp.h5

============
Output Files
============
data/
    *.cum_filt_deramp.h5
outputs/
    cumU_tif/
        *.filt_deramp_cumU.h5
'''
# Change Log
'''
v1.1 20251119, Lu Liang, UoE
 - division function updated.
v1.0.1 20251105, Lu Liang, UoE
 - file directory changed.
v1.0 20251103, Lu Liang, UoE
 - export cumU as GeoTiff function added.
'''

import os
import sys
import h5py
import glob
import time
import rasterio
import numpy as np
from rasterio.transform import from_bounds

author = 'Lu Liang, University of Edinburgh, School of Geosciences'
ver = 'v1.1'
last_update = '2025-11-19'

# path setting
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUT_DIR = os.path.join(BASE_DIR, 'outputs', 'cumU_tif')

os.makedirs(OUT_DIR, exist_ok=True)

H5_SUFFIX = '.cum_filt_deramp.h5'

h5_list = sorted(glob.glob(os.path.join(DATA_DIR, f'*{H5_SUFFIX}')))
# print(h5_list)


def division(dst, geoU):

    if dst.ndim == 3:
        geoU_b = geoU[None, :, :]
        out = dst.astype(np.float32) / geoU_b.astype(np.float32)
    else:
        out = dst.astype(np.float32) / geoU.astype(np.float32)

    return out


def get_transform(corner_lon, corner_lat, post_lon, post_lat, target_h, target_w):
    x = corner_lon + post_lon * (target_w - 1)
    y = corner_lat + post_lat * (target_h - 1)

    left   = min(corner_lon, x) - abs(post_lon)/2
    bottom = min(corner_lat, y) - abs(post_lat)/2
    right  = max(corner_lon, x) + abs(post_lon)/2
    top    = max(corner_lat, y) + abs(post_lat)/2

    transform = from_bounds(left, bottom, right, top, width=target_w, height=target_h)

    return transform


# def write_tif(cumU_last, velU, transform, out_cumU_tif, out_velU_tif):
def write_tif(cumU, transform, out_cumU_tif):
    H, W = cumU.shape
    print('     Writing cumU ...')
    with rasterio.open(out_cumU_tif, 'w', height=H, width=W, transform=transform, crs='EPSG:4326', 
                       dtype=rasterio.float32, count=1, compress='deflate', predictor=2) as dst:
        print(f'Writing cumU as tif: {out_cumU_tif} ...')
        dst.write(cumU, 1)

    # print('     Writing velU ...')
    # with rasterio.open(out_velU_tif, 'w', height=H, width=W, transform=transform, crs='EPSG:4326', 
    #                    dtype=rasterio.float32, count=1, compress='deflate', predictor=2) as dst:
    #     print(f'Writing velU as tif: {out_velU_tif} ...')
    #     dst.write(velU, 1)



if __name__ == '__main__':
    # Start 
    start = time.time()
    print('\n{} ver{} {} {}'.format(os.path.basename(sys.argv[0]), ver, last_update, author))

    for f in h5_list:
        base = os.path.basename(f)[:-len(H5_SUFFIX)]
        print(f'Processing {base} ...')
        
        with h5py.File(f, 'r+') as h5f:
            print('     Reading cum ...')
            ds = h5f['cum']
            T, H, W = ds.shape
            print('     cum read done')
            vel = h5f['vel'][:]
            geoU = h5f['U.geo'][:]
            corner_lon = float(h5f['corner_lon'][()])
            corner_lat = float(h5f['corner_lat'][()])
            post_lon = float(h5f['post_lon'][()])
            post_lat = float(h5f['post_lat'][()])


            print(f'     Creating dataset "cumU" ...')
            if 'cumU' in h5f: del h5f['cumU']
            cumU_ds = h5f.create_dataset('cumU', shape=(T, H, W), dtype='float32',
                                         chunks=True, compression='gzip', compression_opts=4, shuffle=True)


            print(f'     Start dividing cum ...')
            for t in range(T):
                slab = ds[t, :, :]
                cumU_ds[t, :, :] = division(slab, geoU)
            # cumU = division(cum, geoU)
            print(f'     Start dividing vel ...')
            velU = division(vel, geoU)
            # print(f'cumU shape: {cumU.shape}')
            # print(f'velU shape: {cumU.shape}')

            # h5f.create_dataset('cumU', data=cumU)
            print(f'     Creating dataset "velU" ...')
            if 'velU' in h5f: del h5f['velU']
            h5f.create_dataset('velU', data=velU)

            T, H, W = ds.shape
            # H, W = vel.shape[0], vel.shape[1]
            transform = get_transform(corner_lon, corner_lat, post_lon, post_lat, H, W)
            transform = get_transform(corner_lon, corner_lat, post_lon, post_lat, H, W)
            print(velU.shape)
            print(vel.shape)
            cumU_last = cumU_ds[T-1, :, :]
            out_tif = os.path.join(OUT_DIR, f'{base}.filt_deramp_cumU.tif')
            write_tif(cumU_last, transform, out_tif)

    # Finish
    elapsed = time.time() - start
    h = int(elapsed / 3600)
    m = int((elapsed % 3600) / 60)
    s = int(elapsed % 60)
    print('\nElapsed time: {:02}h {:02}m {:02}s'.format(h, m, s))
    print('\n{} successfully finished!\n'.format(os.path.basename(sys.argv[0])))
