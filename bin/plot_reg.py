#!/usr/bin/env python3
'''
Written by Lu Liang, University of Edinburgh, School of Geosciences, 2025.

===========
Description
===========
Script to plot regression between GW change rate and VU
plot regression of csv and a single tif

============
Inputs Files
============
data/
    GWLcr_VU_ModelResult.csv
    vu_shiyang_referenced.tif

============
Output Files
============
outputs/
    reg_GWcr_vs_VUall.png
'''
# Change Log
'''
v1.1 20260330, Lu Liang, UoE
 - Edited into function format.
v1.0.1 20251217, Lu Liang, UoE
 - bug fixed on importing files
v1.0 20251214, Lu Liang, UoE
'''

import os 
import sys
import time
import numpy as np
import pandas as pd
import seaborn as sns
import geopandas as gpd
import matplotlib.pyplot as plt
import statsmodels.api as sm

from plot_ts import load_gw_obs_csv, calc_wls
from gps_reference import OpenTif

# Start
author = 'Lu Liang, University of Edinburgh, School of Geosciences'
ver = 'v1.1'
last_update = '2026-03-30'

start = time.time()
print('\n{} ver{} {} {}'.format(os.path.basename(sys.argv[0]), ver, last_update, author))


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
IN_GW = os.path.join(BASE_DIR, 'data', 'GWLcr_VU_ModelResult.csv')
IN_VU = os.path.join(BASE_DIR, 'outputs', 'gps_ref', 'vu_shiyang_referenced.tif')
VU = os.path.join(BASE_DIR, 'data', 'vu_Shiyang_decomposed.tif')
OUT_DIR = os.path.join(BASE_DIR, 'outputs')
os.makedirs(OUT_DIR, exist_ok=True)   


def plot_reg_allVU(gw_df, vu_raster, out_dir):
    '''
    Extract pixel values from a vu raster at point locations (lon/lat),
    then plot a weighted least squares regression between the extracted
    values and the groundwater change rate.
    '''
    # plot settings
    sns.set_theme(style="whitegrid", context="talk", rc={"grid.linewidth": 0.8})
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    plt.rcParams['xtick.labelsize'] = 12
    plt.rcParams['ytick.labelsize'] = 12

    # convert to GeoDataFrame
    gw_gdf = gpd.GeoDataFrame(gw_df, geometry=gpd.points_from_xy(gw_df['lon'], gw_df['lat']), crs='EPSG:4326')

    # Open vu tif and extract values
    print('Loading in tif file ...')
    vu_tif = OpenTif(vu_raster)
    vals = gw_gdf.geometry.apply(lambda pt: vu_tif.extract_pixel_value(pt.x, pt.y, 8))
    gw_gdf[['vu', 'vu_unc']] = pd.DataFrame(vals.tolist(), index=gw_gdf.index)

    print(gw_gdf[['well_id','lon','lat', 'gw_k_sin', 'gw_k_sin_unc', 'vu','vu_unc']].drop_duplicates().head(5))

    # WLS regression
    gw_cr = gw_gdf['gw_k_sin'].values.astype(float)
    vu = gw_gdf['vu'].values.astype(float)
    rel_model = calc_wls(vu, gw_cr)

    if rel_model is not None:
        c = rel_model.params[0]
        b = rel_model.params[1]
        print(f'gw_cr = {b:.4f} * vu + {c:.4f}')

        plt.figure(figsize=(10, 10), dpi=120)
        sns.scatterplot(data=gw_gdf, x='vu', y='gw_k_sin', color='#6cabeb', edgecolor='dimgray', linewidth=0.4, s=40, alpha=0.5)

        x_line = np.linspace(gw_gdf['vu'].min(), gw_gdf['vu'].max(), 100)
        X_line = sm.add_constant(x_line)
        y_line = rel_model.predict(X_line)

        label_text = f"WLS fit: GW change rate = {b:.4f} * VU + {c:.4f}"
        plt.plot(x_line, y_line, color='darkred', linewidth=1.8, label=label_text)
        plt.legend(loc='upper left', fontsize=12)
        plt.xlabel('Vertical velocity (mm/yr)', fontsize=12)
        plt.ylabel('Groundwater Level Change Rate (m/yr)', fontsize=12)
        plt.title('VU vs groundwater Change Rate', fontsize=14)

        out_path = os.path.join(out_dir, 'reg_GWLcr_vs_VUall.png')
        plt.tight_layout()
        plt.savefig(out_path)
        plt.close()
        print(f'Plot saved to {out_path}.')

    return b, c

if __name__ == '__main__':
    # Start
    start = time.time()
    print('\n{} ver{} {} {}'.format(os.path.basename(sys.argv[0]), ver, last_update, author))

    # Load csv file
    print('Loading in csv file ...')
    gw_df = pd.read_csv(IN_GW)

    plot_reg_allVU(gw_df, VU, OUT_DIR)

    # Finish
    elapsed = time.time() - start
    h = int(elapsed / 3600)
    m = int((elapsed % 3600) / 60)
    s = int(elapsed % 60)
    print('\nElapsed time: {:02}h {:02}m {:02}s'.format(h, m, s))
    print('\n{} successfully finished!\n'.format(os.path.basename(sys.argv[0])))




# gw_gdf['gw_vel'] = np.nan
# gw_gdf['gw_vel_unc'] = np.nan

# for wid, sub in groups:
#     sub = sub.sort_values('date')
#     gw_ts = sub['obs_gw'].values.astype(float)
#     gw_x  = (sub['date'] - sub['date'].min()).dt.days.values.astype(float)

#     gw_model = calc_wls(gw_x, gw_ts)
#     gw_vel_day, gw_unc_day = gw_model.params[1], gw_model.bse[1]

#     # convert gw values from m/day to m/year
#     gw_vel = gw_vel_day * 365.25
#     gw_unc = gw_unc_day * 365.25

#     # append results in gw_gdf
#     mask = gw_gdf['well_id'] == wid
#     gw_gdf.loc[mask, 'gw_vel'] = gw_vel
#     gw_gdf.loc[mask, 'gw_vel_unc'] = gw_unc
