
'''
Tidy version of plot_displacement_ts.py

Editor: Lu
Update: 15 Oct 2025 - read in gw data and hdf5 file correclty
Update: 28 Oct 2025 - plot ts of cum and ground water for specific well
Update: 6  Nov 2025 - output plots path added.
Update: 15 Nov 2025 - WLS fitting function added; plot function updated to show gw AND cum.
Update: 17 Nov 2025 - plot functions updated to avoid duplicate loops.
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
import statsmodels.api as sm



BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
IN_CSV = os.path.join(BASE_DIR, 'data', '2018-2022_ShiyangBasin_Groundwater_WaterLevel.csv')
IN_H5 = os.path.join(BASE_DIR, 'data', '*.cum_filt.h5')
OUT_DIR = os.path.join(BASE_DIR, 'outputs', 'GW_cum_f_ts')
os.makedirs(OUT_DIR, exist_ok=True)

# plot settings
sns.set_theme(style="whitegrid", context="talk", rc={"grid.linewidth": 0.8})
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['xtick.labelsize'] = 12
plt.rcParams['ytick.labelsize'] = 12


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


def calc_wls (x, y, eps=1e-8):
    '''
    Cite: https://www.statsmodels.org/dev/generated/statsmodels.regression.linear_model.OLS.html
    '''
    # clear data (nan will cause error)
    mask = ~np.isnan(x) & ~np.isnan(y)
    x = x[mask]
    y = y[mask]

    # Apply OLS first
    x_const = sm.add_constant(x)
    ols_model = sm.OLS(y, x_const)
    ols_result = ols_model.fit()
    # print(ols_result.summary())
    print(ols_result.t_test([1, 0]))

    # Apply 1st WLS
    abs_res = np.abs(ols_result.resid)                    # absolute residuals: |observed y - fitted y|
    fm_x = sm.add_constant(ols_result.fittedvalues)
    # print(abs_res[:5])
    # print(fm_x[:5])
    var_mod = sm.OLS(abs_res, fm_x).fit()                 # model absolute residuals as function of fitted values
    pred_var = np.clip(var_mod.fittedvalues, eps, None)   # predicted variance: generate variance model form residual to avoid residual=0. variance = b * predicted y + c
    weight1 = 1.0 / (pred_var ** 2)                       # weights: w = 1 / variance^2
    wls1_result = sm.WLS(y, x_const, weights=weight1).fit()
    # print(wls1_result.summary())
    print(wls1_result.t_test([1, 0]))

    # Apply 2nd WLS
    abs_res2 = np.abs(wls1_result.resid)
    fm_x2 = sm.add_constant(wls1_result.fittedvalues)
    var_mod2 = sm.OLS(abs_res2, fm_x2).fit()
    pred_var2 = np.clip(var_mod2.fittedvalues, eps, None)
    wt2 = 1.0 / (pred_var2 ** 2)
    wls2_result = sm.WLS(y, x_const, weights=wt2).fit()
    # print(wls2_result.summary())
    print(wls2_result.t_test([1, 0]))

    # return wls2_fit


def plot_ts(df, lon_idx, lat_idx, cum, dt, frame_base):
    '''
    Function to plot groundwater and cum displacement ts
    of coords that located within each hdf5 files
    '''
    groups = df.groupby('well_id')
    # print(groups.groups.keys())
    plotted = 0
    # select cum form choosen lon/lat_idx
    for wid, xi, yi in zip(groups.groups.keys(), lon_idx, lat_idx):    # zip() to iterate two lists together
        # print(wid, xi, yi)
        # xi, yi = int(xi), int(yi)
        cum_ts = cum[:, yi, xi].astype(float)
        if not np.isfinite(cum_ts).any():
            continue
        sub = groups.get_group(wid).sort_values('date')

        # plot
        fig, ax = plt.subplots(figsize=(12, 7), dpi=50)
        ax2 = ax.twinx()

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

        plt.savefig(os.path.join(OUT_DIR, f'F{frame_base}_W{wid}.png'))
        # plt.show()
        # plt.close(fig)
        plotted += 1
    print(f'Total {plotted} out of {len(groups.groups.keys())} wells plotted for frame {frame_base}.')



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
    print(f'CSV data loaded successfully.')


    # 2) load hdf5 files
    # 2.1 select all wells, and avoid duplicates
    wells = df[['well_id', 'lon', 'lat']].drop_duplicates('well_id')
    print(f'Total {wells.shape[0]} wells found in CSV.')

    # 2.2 get h5 filenames
    h5_fn = sorted(glob.glob(IN_H5))
    print(f'Total {len(h5_fn)} hdf5 found.')

    # 2.3 read in h5
    for fn in h5_fn:
        frame_base = os.path.basename(fn).split('.cum_filt.h5')[0]
        print(f'Processing {frame_base} ...')

        f = h5.File(fn, 'r')

        # get lon and lat values
        lon = get_dim(f, 'lon')
        lat = get_dim(f, 'lat')

        # get vel values
        cum = f['cum'][:]

        # get imdates
        imdates = f['imdates'][:]
        dt = [datetime.datetime.strptime(str(date), "%Y%m%d") for date in imdates]

        # find closest index for each well
        lon_idx = [find_closest_index(lon, lon_x) for lon_x in wells['lon']]
        lat_idx = [find_closest_index(lat, lat_x) for lat_x in wells['lat']]
        # print(df['lon'][:5])
        # print(lon_idx[:5])
        # print(df['lat'][:5])
        # print(lat_idx[:5])



    # # 3) WLS model
    # # 3.1 WLS for obs_gw vs date
    # # for each wells
    # sub = df[df['well_id'] == 'wid'].sort_values('date')
    # # sub = df[df['well_id'] == '620302210010'].sort_values('date') 
    # x_gw = (sub['date'] - sub['date'].min()).dt.days.values.astype(float)
    # y_gw = sub['obs_gw'].values.astype(float)
    # print(f'Well {'well_id'}: x size = {x_gw.size}, y size = {y_gw.size}')

    # calc_wls(x_gw, y_gw)
    

    plot_ts(df, lon_idx, lat_idx, cum, dt, frame_base)
        
