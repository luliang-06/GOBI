#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
3 Nov 25 updated: export cumU as GeoTiff added.
'''

import os
import h5py
import glob
import rasterio
import numpy as np
from rasterio.transform import from_bounds

# path setting
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')

H5_SUFFIX = '.cum_filt_deramp.h5'

h5_list = sorted(glob.glob(os.path.join(DATA_DIR, f'*{H5_SUFFIX}')))
# print(h5_list)


def division(dst, geoU):
    print(f'Start dividing ...')
    geoU_b = geoU[None, :, :]
    out = dst.astype(np.float32) / geoU_b.astype(np.float32)
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


def write_tif(cumU_last, transform, out_cumU_tif):
    with rasterio.open(out_cumU_tif, 'w', height=H, width=W, transform=transform, crs='EPSG:4326', 
                       dtype=rasterio.float32, count=1, compress='deflate', predictor=2) as dst:
        print(f'Writing cumU as tif: {out_cumU_tif} ...')
        dst.write(cumU_last, 1)

    # with rasterio.open(out_velU_tif, 'w', height=H, width=W, transform=transform, crs='EPSG:4326', 
    #                    dtype=rasterio.float32, count=1, compress='deflate', predictor=2) as dst:
    #     print(f'Writing velU as tif: {out_velU_tif} ...')
    #     dst.write(velU_last, 1)



if __name__ == '__main__':
    for f in h5_list:
        base = os.path.basename(f)[:-len(H5_SUFFIX)]
        print(f'Processing {base} ...')
        
        with h5py.File(f, 'r+') as h5f:
            cum = h5f['cum'][:]
            vel = h5f['vel'][:]
            geoU = h5f['U.geo'][:]
            corner_lon = float(h5f['corner_lon'][()])
            corner_lat = float(h5f['corner_lat'][()])
            post_lon = float(h5f['post_lon'][()])
            post_lat = float(h5f['post_lat'][()])

            # cumU = h5f['cumU'][:]

            cumU = division(cum, geoU)
            # velU = division(vel, geoU)
            print(f'cumU shape: {cumU.shape}')
            # print(f'velU shape: {cumU.shape}')
            # h5f.create_dataset('cumU', data=cumU)
            # h5f.create_dataset('velU', data=velU)

            H, W = cum.shape[1], cum.shape[2]
            transform = get_transform(corner_lon, corner_lat, post_lon, post_lat, H, W)

            cumU_last = cumU[-1, :, :]
            out_tif = os.path.join(DATA_DIR, f'{base}.filt_deramp.cumU.tif')
            write_tif(cumU_last, transform, out_tif)

    print('Finished.')
