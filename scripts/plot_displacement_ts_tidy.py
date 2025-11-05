#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Scripts wrote by Lu 
But still a lot bugs...

Editor: Lu
Last edit date: 6 Oct 2025
'''

import os
import re
import glob
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import pandas as pd
import h5py as h5
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Path Settings & Variables
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

IN_CSV = os.path.join(BASE_DIR, 'data', '2018-2022石羊河地下水监测井数据_水位_fixed.csv')
IN_H5 = os.path.join(BASE_DIR, 'data', '*.h5')

OUT_DIR = os.path.join(BASE_DIR, 'Outputs', 'ts_combined')
PLOT_DIR = os.path.join(OUT_DIR, 'plots')

# A & D Frame Pairs
FRAME_PAIRS = [
    ('128A_05172','033D_05106'),
    ('055A_05021','135D_05023'),
    ('055A_05221','135D_05222'),
]

# Plotting Setting
sns.set_theme(style='whitegrid', context='talk')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']

plt.rcParams['xtick.labelsize'] = 12
plt.rcParams['ytick.labelsize'] = 12


# ========================
# CSV loader
# ========================
def load_csv(in_csv):
    '''
    Function to 
    1) load input csv,
    2) list key columns, 
    3) convert year col and obs_date col to datetime,
    4) numeric values from string to float,
    5) clean data,
    6) melt data into a long dataframe.
    '''
    # Open csv
    df = pd.read_csv(in_csv, dtype=str)
    print(df[:])
    df.columns = df.columns.str.strip()

    # rename columns
    rename_map = {'统一编号': 'well_id',
                  '年份': 'year',
                  '经度': 'lon',
                  '纬度': 'lat',
                  '地面高程/米': 'elevation_m'}
    
    df = df.rename(columns=rename_map)

    # convert well_id to string
    if 'well_id' in df.columns:
        df['well_id'] = df['well_id'].astype(str)
        df['well_id'] = (df['well_id'].str.strip())

    # Key columns check
    key_columns = ['well_id', 'year']
    for col in key_columns:
        if col not in df.columns:
            raise KeyError(f"缺少必需列：{col} (请确认原表是否包含 '统一编号' 和 '年份')")

    # Observation Date Columns
    pattern = re.compile(r'^M\d{2}_D\d{2}$')
    day_cols = [c for c in df.columns if pattern.match(str(c))]
    if not day_cols:  # 如果没有找到day_col则返回长表
        return pd.DataFrame(columns=[
            'well_id','year','date','obs_date','gw_level_m','lon','lat','elevation_m'
        ])

    # Melt to long table
    df_csv_long = df.melt(
        id_vars=['well_id', 'year', 'lon', 'lat', 'elevation_m'],
        value_vars=day_cols,
        var_name='obs_date',
        value_name='gw_level_m'
    )

    # Numeric column values
    df_csv_long['gw_level_m'] = pd.to_numeric(df_csv_long['gw_level_m'], errors='raise')
    for c in ['year', 'lon', 'lat', 'elevation_m']:
        df_csv_long[c] = pd.to_numeric(df_csv_long[c], errors='raise')

    # Convert dates to datetime
    md = df_csv_long['obs_date'].str.extract(r'M(\d{2})_D(\d{2})').astype(float)
    df_csv_long['month'] = md[0]
    df_csv_long['day'] = md[1]
    df_csv_long = df_csv_long.dropna(subset=['year', 'month', 'day'])

    df_csv_long['date'] = pd.to_datetime(
        {
        'year':  df_csv_long['year'].astype(int),
        'month': df_csv_long['month'].astype(int),
        'day':   df_csv_long['day'].astype(int)
        },
        errors='coerce'
    )

    # Clean up values with no date / gw_level_m
    df_csv_long = df_csv_long.dropna(subset=['date', 'gw_level_m']).reset_index(drop=True)

    print(f'[CSV loader] input csv loaded successful')
    print(df_csv_long.head())

    return df_csv_long

# ========================
# HDF5 loaders & tools
# ========================
def get_dim(h5_file, dim_name):
    '''
    function to get x / y values:
    '''
    # get number of points from 'cum':
    if dim_name == 'lon':
        var_sz = h5_file['cum'].shape[2]
    else:
        var_sz = h5_file['cum'].shape[1]
    # get corner / min value:
    var_name = 'corner_{0}'.format(dim_name)
    var_min = h5_file[var_name][()]
    # get offset / increment value:
    var_name = 'post_{0}'.format(dim_name)
    var_inc = h5_file[var_name][()]
    # create list of values:
    var_val = [round((i * var_inc) + var_min, 4) for i in range(0, var_sz)]
    # return the values
    return var_val


def find_closest_index(array, value):
    '''
    Find the index of the closest value in the array.
    '''
    array = np.array(array)  # Convert the list to a NumPy array
    return (np.abs(array - value)).argmin()


def scan_hdf5_meta(h5_path: str) -> dict:
    '''
    Function to calculate geographic area covered by each hdf5 files
    筛选/定界
    '''
    with h5.File(h5_path, 'r') as f:
        # Image size (time: nt, column (lon): nx, row (lat): ny)
        ny = f['cum'].shape[1]
        nx = f['cum'].shape[2]
        
        # 起点 & 步长 of image on geography
        corner_lon = float(f['corner_lon'][()]) # lon start point (top left corner/reference)
        post_lon   = float(f['post_lon'][()])   # lon step (can be positive or negative)
        corner_lat = float(f['corner_lat'][()]) # lat start point
        post_lat   = float(f['post_lat'][()])   # lat step

    # calculate the geographic area covered by image using reference lon&lat and posts
    lon_last = corner_lon + (nx - 1) * post_lon
    lat_last = corner_lat + (ny - 1) * post_lat
    lon_min, lon_max = (min(corner_lon, lon_last), max(corner_lon, lon_last))
    lat_min, lat_max = (min(corner_lat, lat_last), max(corner_lat, lat_last))

    # pack as a dictionary for later use
    return dict(
        path=h5_path, nx=nx, ny=ny, 
        corner_lon=corner_lon, post_lon=post_lon,
        corner_lat=corner_lat, post_lat=post_lat,
        lon_min=lon_min, lon_max=lon_max,
        lat_min=lat_min, lat_max=lat_max,
        base=os.path.basename(h5_path)
    )

'''
Following two functions can took the place of meshgrid
'''
def point_in_meta(meta, lon, lat, eps=1e-12):
    '''
    Function to check if a given lon&lat is covered by hdf5 file area
    '''
    return (meta['lon_min'] - eps <= lon <= meta['lon_max'] + eps) and \
           (meta['lat_min'] - eps <= lat <= meta['lat_max'] + eps)


def coords_to_index(start: float, post: float, n: int, coord: float) -> int:
    '''
    Funtion to convert a given lon&lat into index
    in order to extract cum displacement from hdf5 files
    '''
    if post == 0:
        return 0
    ix = int(round((coord - start) / post))
    return max(0, min(n - 1, ix))


def set_pairs (base: str):
    '''
    Function to divide hdf5 files in ascending group and descending group
    '''
    for a, d in FRAME_PAIRS:
        if base.startswith(a): return f'{a}__{d}', 'A'
        if base.startswith(d): return f'{a}__{d}', 'D'
    return None, None


def load_hdf5(h5_path: str, lon_pt: float, lat_pt:float) -> pd.DataFrame:
    '''
    Funcrtion to extract cum displacement from point input
    '''
    # Open h5 file
    with h5.File(h5_path, 'r') as f:
        ny, nx = f['cum'].shape[1], f['cum'].shape[2]
        corner_lon = float(f['corner_lon'][()])
        post_lon   = float(f['post_lon'][()])
        corner_lat = float(f['corner_lat'][()])
        post_lat   = float(f['post_lat'][()])

        ix = coords_to_index(corner_lon, post_lon, nx, lon_pt)
        iy = coords_to_index(corner_lat, post_lat, ny, lat_pt)
    
        ts      = f['cum'][:, iy, ix]
        imdates = f['imdates'][:] if 'imdates' in f else np.arange(ts.shape[0])

    dt = pd.to_datetime(imdates.astype(str), format='%Y%m%d', errors='coerce')

    df_hdf5 = pd.DataFrame({
        'date': dt,
        'displacement': ts.astype(float),
        'lon': lon_pt, 'lat': lat_pt,
        'ix': ix, 'iy': iy,
        'h5': os.path.basename(h5_path),
    }).dropna(subset=['date'])

    return df_hdf5

# ========================
# plotting
# ========================
def plot_ad_gw(well_id: str,
               dfA: pd.DataFrame, dfD: pd.DataFrame, dfGW: pd.DataFrame,
               save_path: str, elev: Optional[float] = None,
               pair_key: Optional[str] = None):
    
    fig, ax_gw = plt.subplots(figsize=(12,7), dpi=180)
    ax_insar = ax_gw.twinx()

    # GW
    if dfGW is not None and not dfGW.empty:
        dfGW = dfGW.sort_values('date')
        sns.scatterplot(data=dfGW, x='date', y='gw_level_m', ax=ax_gw, 
                        s=50, alpha=0.5, facecolor='grey', edgecolor='dimgray', linewidth=0.8,
                        label='Groundwater', legend=True
                        )
        
    # Ascending
    if dfA is not None and not dfA.empty:
        dfA = dfA.sort_values('date')
        sns.scatterplot(data=dfA, x='date', y='displacement', ax=ax_insar,
                        s=50, alpha=0.5, facecolor='steelblue', edgecolor='navy', linewidth=0.8,
                        label='A LOS', legend=True
                        )
    
    # Descending
    if dfD is not None and not dfD.empty:
        dfD = dfD.sort_values('date')
        sns.scatterplot(data=dfD, x='date', y='displacement', ax=ax_insar,
                        s=50, alpha=0.5, facecolor='steelblue', edgecolor='navy', linewidth=0.8,
                        label='D LOS', legend=True
                        )
    
    # title / labels
    # set frame name for demonstrate
    def frames_from_df(df: Optional[pd.DataFrame]) -> str:
        if df is None or df.empty or 'h5' not in df.columns:
            return 'NA'
        bases = sorted(set(df['h5'].astype(str).str.split('_').str[:2].str.join('_')))
        # set first two token as frame demonstration name
        return ','.join(bases) if bases else 'NA'
    
    title_frames = []
    
    a_frames = frames_from_df(dfA)
    d_frames = frames_from_df(dfD)
    title_frames.append(f'A[{a_frames}] D[{d_frames}]')

    elev_txt = f'{elev:.2f} m' if isinstance(elev, (int, float, np.floating)) else 'NA'

    title = f'Well ID: {well_id} | ' + ' | '.join(title_frames) + f' | Elev: {elev_txt}'

    ax_gw.set_title(title, fontsize=12)

    ax_gw.set_xlabel('Date')
    ax_gw.set_ylabel('Groundwater level (m)')
    ax_insar.set_ylabel('LOS Displacement (mm)')

    ax_gw.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax_gw.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax_gw.xaxis.get_major_locator()))

    # Combine legends of GW & AnD
    h1, l1 = ax_gw.get_legend_handles_labels()
    h2, l2 = ax_insar.get_legend_handles_labels()
    handles = []
    labels = []
    if h1 and l1:
        handles += h1; labels += l1
    if h2 and l2:
        for hh, ll in zip(h2, l2):
            if ll not in labels:
                handles.append(hh); labels.append(ll)

    if handles:
        ax_insar.legend(handles, labels, loc='upper left', frameon=False, fontsize=9)

    fig.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    # print(f'[Plot] Save path created: {save_path}')
    fig.savefig(save_path, dpi=180)
    plt.close(fig)


# Main Function
def main():
    # 0. Make output dirction
    os.makedirs(OUT_DIR, PLOT_DIR, exist_ok=True)
    
    # 1. Read in CSV file
    df_csv_long = load_csv(IN_CSV)

    # 2. scan meta data for all hdf5 files
    metas = [scan_hdf5_meta(p) for p in sorted(glob.glob(IN_H5))]
    
    # 3. Build a list to store well_id and its location 
    points = (df_csv_long[['well_id', 'lon', 'lat']]
              .dropna(subset=['lon', 'lat'])
              .drop_duplicates()
              .reset_index(drop=True)
              )
    
    total_plots = 0

    # tasks = []    # (well_id, lon, lat, pair_key, meta_for_A, meta_for_D)
    for _, row in points.iterrows():
        well_id = row['well_id']
        lon_pt = float(row['lon'])
        lat_pt = float(row['lat'])
        
        # 3a. find hdf5 files that cover this point
        covered = [m for m in metas if point_in_meta(m, lon_pt, lat_pt)]
        if not covered:
            continue

        # 3b. assigned covered hdf5 to A&D pairs
        bucket: Dict[str, dict[str, List[Dict[str, Any]]]] = {}
        for m in covered:
            pair_key, side = set_pairs(m['base'])
            if pair_key and side in ('A', 'D'):
                bucket.setdefault(pair_key, {}).setdefault(side, []).append(m)

        valid_pairs = [(pair_key, sides) for pair_key, sides in bucket.items() if 'A' in sides and 'D' in sides]
        if not valid_pairs:
            continue
        
        # 3c. for each pairs of each location, plot
        # GW
        dfGW = df_csv_long[df_csv_long['well_id'] == well_id][['date', 'gw_level_m']].sort_values('date')

        # elev
        e = df_csv_long.loc[df_csv_long['well_id'] == well_id, 'elevation_m'].dropna()
        elev = float(e.iloc[0]) if len(e) else None

        for pair_key, sides in valid_pairs:
            metasA = sides['A']
            metasD = sides['D']

            # extract ts of displacement from load_hdf5
            dfA_List = [load_hdf5(m['path'], lon_pt, lat_pt) for m in metasA]
            dfD_List = [load_hdf5(m['path'], lon_pt, lat_pt) for m in metasD]
            dfA = pd.concat(dfA_List, ignore_index = True) if dfA_List else pd.DataFrame(columns=['date', 'displacement', 'h5'])
            dfD = pd.concat(dfD_List, ignore_index = True) if dfD_List else pd.DataFrame(columns=['date', 'displacement', 'h5'])

            # plot
            save_name = f'{well_id}_{pair_key}.png'
            save_path = os.path.join(PLOT_DIR, save_name)
            plot_ad_gw(well_id, dfA, dfD, dfGW, save_path, elev=elev, pair_key=pair_key)
            
            total_plots += 1
            print(f'[plotting] well={well_id} pair={pair_key}')

    print(f'[Finished] Total {total_plots} plots generated, saved to: {PLOT_DIR}')

if __name__ == '__main__':
    main()