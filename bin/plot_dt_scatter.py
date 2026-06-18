#!/usr/bin/env python3
'''
Written by Lu Liang, University of Edinburgh, School of Geosciences, 2026.

===========
Description
===========
Script to plot scatter of delta_t vs amplitude (top) and delta_t vs velocity
(bottom) for each InSAR frame.

============
Inputs Files
============
frames/
    */TS_GEOCml1GACOS/
        cum_filt.h5_delta_t.geo.tif
        cum_filt.h5_amp.geo.tif
        cum_filt.h5_vel.geo.tif

============
Output Files
============
outputs/
    dt_scatter_{frame_id}.png
'''
# Change Log
'''
v1.0 20260402, Lu Liang, UoE
'''

import os
import sys
import glob
import time
import numpy as np
from osgeo import gdal
import matplotlib.pyplot as plt
import seaborn as sns

author = 'Lu Liang, University of Edinburgh, School of Geosciences'
ver = 'v1.0'
last_update = '2026-04-02'

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FRAMES_DIR = os.path.join(BASE_DIR, 'frames')
OUT_DIR = os.path.join(BASE_DIR, 'outputs')
os.makedirs(OUT_DIR, exist_ok=True)

MAX_POINTS = 50000   # downsample to this many points for scatter plot


def load_tif(path):
    '''Read a single-band GeoTIFF and return a 2-D float array (NaN for nodata).'''
    ds = gdal.Open(path)
    if ds is None:
        raise FileNotFoundError(f'Cannot open: {path}')
    band = ds.GetRasterBand(1)
    nodata = band.GetNoDataValue()
    arr = band.ReadAsArray().astype(float)
    if nodata is not None:
        arr[arr == nodata] = np.nan
    return arr


def find_tif(ts_dir, stem):
    '''
    Return the first tif in ts_dir whose name starts with stem (e.g.
    "cum_filt.h5_delta_t"), or None if not found.
    '''
    matches = glob.glob(os.path.join(ts_dir, stem + '*.tif'))
    return matches[0] if matches else None


def plot_dt_scatter(ts_dir, frame_id, out_dir):
    '''
    Plot 2-panel scatter: delta_t vs amplitude (top) and delta_t vs velocity
    (bottom) for a single frame. Saves a PNG to out_dir.
    '''
    dt_path  = find_tif(ts_dir, 'cum_filt.h5_delta_t')
    amp_path = find_tif(ts_dir, 'cum_filt.h5_amp')
    vel_path = find_tif(ts_dir, 'cum_filt.h5_vel')

    # load data
    dt  = load_tif(dt_path)
    amp = load_tif(amp_path)
    vel = load_tif(vel_path)


    # --- plot settings ---
    sns.set_theme(style='whitegrid', context='talk', rc={'grid.linewidth': 0.8})
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    plt.rcParams['xtick.labelsize'] = 12
    plt.rcParams['ytick.labelsize'] = 12

    fig, axes = plt.subplots(2, 1, figsize=(10, 10), dpi=120)

    # --- top panel: delta_t vs amplitude ---
    mask = np.isfinite(dt) & np.isfinite(amp)
    x_amp, y_amp = amp[mask].ravel(), dt[mask].ravel()
    if len(x_amp) > MAX_POINTS:
        idx = np.random.choice(len(x_amp), MAX_POINTS, replace=False)
        x_amp, y_amp = x_amp[idx], y_amp[idx]

    axes[0].scatter(x_amp, y_amp, s=1, alpha=0.5, color='#6cabeb', edgecolors='none')
    axes[0].set_xlabel('Amplitude', fontsize=12)
    axes[0].set_ylabel('Change in \u0394t (days)', fontsize=12)
    axes[0].set_title(f'\u0394t vs Amplitude', fontsize=13)
    axes[0].set_xlim(np.nanpercentile(x_amp, 1), np.nanpercentile(x_amp, 99))


    # --- bottom panel: delta_t vs velocity ---
    mask = np.isfinite(dt) & np.isfinite(vel)
    x_vel, y_vel = vel[mask].ravel(), dt[mask].ravel()
    if len(x_vel) > MAX_POINTS:
        idx = np.random.choice(len(x_vel), MAX_POINTS, replace=False)
        x_vel, y_vel = x_vel[idx], y_vel[idx]

    axes[1].scatter(x_vel, y_vel, s=1, alpha=0.5, color='#e07b6c', edgecolors='none')
    axes[1].set_xlabel('Velocity (mm/yr)', fontsize=12)
    axes[1].set_ylabel('Change in \u0394t (days)', fontsize=12)
    axes[1].set_title(f'\u0394t vs Velocity', fontsize=13)
    axes[1].set_xlim(np.nanpercentile(x_vel, 1), np.nanpercentile(x_vel, 99))


    fig.suptitle(frame_id, fontsize=14, fontweight='bold')
    plt.tight_layout()

    out_path = os.path.join(out_dir, f'dt_scatter_{frame_id}.png')
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f'Saved: {out_path}')


if __name__ == '__main__':
    start = time.time()
    print('\n{} ver{} {} {}'.format(os.path.basename(sys.argv[0]), ver, last_update, author))

    ts_dirs = sorted(glob.glob(os.path.join(FRAMES_DIR, '*', 'TS_GEOCml1GACOS')))
    print(f'\nFound {len(ts_dirs)} frame(s).')

    for ts_dir in ts_dirs:
        frame_id = os.path.basename(os.path.dirname(ts_dir))
        print(f'\nProcessing: {frame_id}')
        plot_dt_scatter(ts_dir, frame_id, OUT_DIR)

    # Finish
    elapsed = time.time() - start
    h = int(elapsed / 3600)
    m = int((elapsed % 3600) / 60)
    s = int(elapsed % 60)
    print('\nElapsed time: {:02}h {:02}m {:02}s'.format(h, m, s))
    print('\n{} successfully finished!\n'.format(os.path.basename(sys.argv[0])))
