
'''
Tidy version of plot_displacement_ts.py

Editor: Lu
Update: 15 Oct 2025 - read in gw data and hdf5 file correclty
Update: 28 Oct 2025 - plot ts of cum and ground water for specific well
Update: 6  Nov 2025 - output plots path added.
'''

import os 
import re
import glob
import datetime
import h5py as h5
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns



BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
IN_CSV = os.path.join(BASE_DIR, 'data', '2018-2022_ShiyangBasin_Groundwater_WaterLevel.csv')
IN_H5 = os.path.join(BASE_DIR, 'data', '*.cum_filt.h5')
OUT_DIR = os.path.join(BASE_DIR, 'outputs', 'GW_cum_f_ts')
os.makedirs(OUT_DIR, exist_ok=True)


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
    """Find the index of the closest value in the array."""
    array = np.array(array)  # Convert the list to a NumPy array
    return (np.abs(array - value)).argmin()

def plot_ts(cum, lon_idx, lat_idx, dt, df, coords, frame_base):
    '''
    Function to plot groundwater and cum displacement ts
    of coords that located within each hdf5 files
    '''

    print(f'Processing {frame_base} ...')

    for i, (xi, yi) in enumerate(zip(lon_idx, lat_idx)):

        xi, yi = int(xi), int(yi)
        cum_ts = cum[:, yi, xi].astype(float)
        # print(i, xi, yi, cum_ts.shape)

        # select specific obs_gw by well_id
        wid = coords.loc[i, 'well_id']
        sub = df[df['well_id'] == wid]

        # try plot
        fig, ax = plt.subplots(figsize=(12, 7), dpi=180)
        ax2 = ax.twinx()

        sns.set_theme(style="whitegrid", context="talk", rc={"grid.linewidth": 0.8})
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans']

        # plot groundwater level
        sns.scatterplot(
            x=sub['date'], y=sub['obs_gw'], ax=ax, 
            s=50, alpha=0.5, facecolor='steelblue', edgecolor='navy', linewidth=0.8,
            label='Ground Water Level', legend=False
        )

        # plot cummulative displacement
        sns.scatterplot(
            x=dt, y=cum_ts, ax=ax2, 
            s=50, alpha=0.5, facecolor='grey', edgecolor='dimgray', linewidth=0.8,
            label='Cum displacement', legend=False
        )

        # ax settings
        ax.set_title(f'Well ID: {wid} Frame: {frame_base}', fontsize=12)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Ground Water Level (m)', fontsize=12)
        ax2.set_ylabel('LOS Displacement (mm)', fontsize=12)
        ax.grid(linestyle='--', alpha=0.5, color='steelblue')
        ax.relim()
        ax.autoscale()
        # keep 2 decimal places 
        ax.ticklabel_format(style='plain', axis='y', useOffset=False)
        ax.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.2f'))

        plt.rcParams['xtick.labelsize'] = 12
        plt.rcParams['ytick.labelsize'] = 12

        plt.savefig(os.path.join(OUT_DIR, f'F{frame_base}_W{wid}.png'))
        plt.close(fig)



if __name__ == '__main__':
    # 1) load csv
    df = pd.read_csv(IN_CSV)
    # print(df.head(5))
    # print(df.columns.tolist())

    # 1.1 rename col name into english
    df = df.rename(columns={'统一编号':'well_id',
                            '年份':'year',
                            '经度':'lon', 
                            '纬度':'lat', 
                            '地面高程/米':'elevation'
                            })

    # 1.2 convert well_id to str to avoid scientific rotation
    df['well_id'] = df['well_id'].astype(str)

    # 1.3 set cols named in pattern 'Mxx_Dxx' as day_cols
    pattern = re.compile(r'M\d{2}_D\d{2}$')
    day_cols = [c for c in df.columns if pattern.match(str(c))]
    # print(day_cols)

    # 1.4 melt wide csv -> long csv
    df = df.melt(id_vars=['well_id', 'year', 'lon', 'lat', 'elevation'],
                value_vars=day_cols,
                var_name='obs_date',
                value_name='obs_gw'
                )

    # 1.5 convert date to datetime
    md = df['obs_date'].str.extract(r'M(\d{2})_D(\d{2})').astype(float)
    # print(md)
    df['month'] = md[0]
    df['day'] = md[1]
    df['year'] = pd.to_numeric(df['year'])

    df['date'] = pd.to_datetime(
        df['year'].astype(int).astype(str) +
        df['month'].astype(int).astype(str).str.zfill(2) +
        df['day'].astype(int).astype(str).str.zfill(2)
    )
    # print(f'Data type check:')
    # print(df[:].dtypes.to_string()) # '.to_string()' is used to hide series dtype printed automatically
    # print(f'csv sample check:')
    # print(df.iloc[:11, :])



    # 2) load hdf5
    # make df with only useable variables
    coords = df[['well_id', 'lon', 'lat']]
    
    # get h5 filenames
    h5_fn = sorted(glob.glob(IN_H5))
    # print(h5_fn)
    print(f'Total {len(h5_fn)} hdf5 found.')
    # read in h5
    for fn in h5_fn:
        frame_base = os.path.basename(fn).split('.cum_filt.h5')[0]

        with h5.File(fn, 'r') as f:
            # print(f.filename)

            # get lon and lat values
            lon = get_dim(f, 'lon')
            lat = get_dim(f, 'lat')
            # print(f'lon: {lon}')
            # print(f'lat: {lat}')

            # grid_lon, grid_lat = np.meshgrid(lon, lat)

            lon_idx = [find_closest_index(lon, lon_x) for lon_x in coords['lon']]
            lat_idx = [find_closest_index(lat, lat_x) for lat_x in coords['lat']]
            # print(f'LON:')
            # print(df['lon'][:5])
            # print(lon_idx[:5])
            # print(f'LAT:')
            # print(df['lat'][:5])
            # print(lat_idx[:5])

            # get vel values
            cum = f['cum'][:]
            # print(cum_val)

            # get imdates
            imdates = f['imdates'][:]
            # print(imdates)
            dt = [datetime.datetime.strptime(str(date), "%Y%m%d") for date in imdates]
            # print(dt)

        plot_ts(cum, lon_idx, lat_idx, dt, df, coords, frame_base)

        
