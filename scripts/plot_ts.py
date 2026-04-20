#!/usr/bin/env python3
'''
Written by Lu Liang, University of Edinburgh, School of Geosciences, 2025.

===========
Description
===========
This scripts plot time series of groundwater level and cummulative deformation.
Do the linear or sinusoidal model of time seires and plot the seasonal components (if sinusoidal model applied)
Export the model fit results into a csv.
Plot the regression between groundwater level and Vu while return a function between tow parameters.

============
Inputs Files
============
data/
    2018-2022_ShiyangBasin_Grounswater_EaterLevel_FIXED.csv
    fid*.cum.h5

=============
Outputs Files
=============
outputs/
    GWL_VU_ts/
        F{frameID}_W{wellID}.png
    GWLvsVU.png
data/
    GWL_VU_ModelResult.csv
'''
# Change Log:
'''
v1.3.2 20260323, Lu Liang, UoE
 - optional sin component subplot added as optional.
v1.3.1 20260322, Lu Liang, UoE
 - unfilted cum ts plot as optional; model results append updated.
v1.3 20260316, Lu Liang, UoE
 - sinusoidal fitting line for time series added.
v1.2.1 20251119, Lu Liang, UoE
 - WLS fitting function applied and export to csv; plot_ts function updated to add plots of wls results; vel plot function added.
v1.2 20251115, Lu Liang, UoE
 - WLS fitting function added; plot function updated to show gw AND cum.
v1.1 20251028, Lu Liang, UoE
 - time series plot of cum and groundwater level for specific well.
v1.0 20251015, Lu Liang, UoE
 - csv & tif read in module created.
'''


import os 
import re
import sys
import glob
import time
import datetime
import h5py as h5
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.dates as mdates
import seaborn as sns
import statsmodels.api as sm
from scipy.optimize import curve_fit

author = 'Lu Liang, University of Edinburgh, School of Geosciences'
ver = 'v1.3.1'
last_update = '2026-03-23'


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
IN_CSV = os.path.join(BASE_DIR, 'data', '2018-2022_ShiyangBasin_Groundwater_WaterLevel_FIXED.csv')
IN_H5 = os.path.join(BASE_DIR, 'data', '*.cum_filt_deramp.h5')
IN_H5_UNFILT = os.path.join(BASE_DIR, 'data', '*.cum.h5')
OUT_DIR = os.path.join(BASE_DIR, 'outputs', 'GWL_VU_ts')

PLOT_UNFILT = True
PLOT_SEASON_COMP = True

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

def load_gw_obs_csv(in_csv):
    # 1) load csv
    df = pd.read_csv(in_csv)
    # print(df.head(5))
    # print(df.columns.tolist())

    # 1.1 rename col name into english
    # df = df.rename(columns={'统一编号':'well_id',
    #                         '年份':'year',
    #                         '经度':'lon', 
    #                         '纬度':'lat', 
    #                         '地面高程/米':'elevation'
    #                         })
    df = df.rename(columns={'wid':'well_id',
                        'year':'year',
                        'lon':'lon', 
                        'lat':'lat', 
                        'elevation(m)':'elevation'
                        })

    # 1.2 convert well_id to str to avoid scientific rotation
    df['well_id'] = df['well_id'].astype(str)

    # 1.3 set cols named in pattern 'Mxx_Dxx' as day_cols
    pattern = re.compile(r'M\d{2}_D\d{2}$')
    day_cols = [c for c in df.columns if pattern.match(str(c))]

    # 1.4 melt wide csv -> long csv
    df = df.melt(id_vars=['well_id', 'year', 'lon', 'lat', 'elevation'],
                value_vars=day_cols,
                var_name='obs_date',
                value_name='obs_gw'
                )

    # 1.5 convert date to datetime
    md = df['obs_date'].str.extract(r'M(\d{2})_D(\d{2})').astype(float)
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

    return df

def calc_wls(x, y, eps=1e-8):
    '''
    Cite: https://www.statsmodels.org/dev/generated/statsmodels.regression.linear_model.OLS.html
    '''
    # clear data (nan will cause error)
    x = np.asarray(x, float)
    y = np.asarray(y, float)

    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    
    # skip nan or insufficient data
    if x.size < 2:
        return None

    # Apply OLS first
    x_const = sm.add_constant(x)
    ols_model = sm.OLS(y, x_const)
    ols_result = ols_model.fit()
    # print(ols_result.summary())

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

    # Apply 2nd WLS
    abs_res2 = np.abs(wls1_result.resid)
    fm_x2 = sm.add_constant(wls1_result.fittedvalues)
    var_mod2 = sm.OLS(abs_res2, fm_x2).fit()
    pred_var2 = np.clip(var_mod2.fittedvalues, eps, None)
    wt2 = 1.0 / (pred_var2 ** 2)
    wls2_result = sm.WLS(y, x_const, weights=wt2).fit()
    # print(wls2_result.summary())

    return ols_result
# , wls2_result

def calc_sin(x, y):
    # clean data
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]

    if x.size < 5:
        return None

    # define sinusoidal model (plus long-term linear trend)
    def sin_model(t, A, T, phi, k, c):  # curve_fit(independent variable, dependent variable1, dependent variable2, ...)
        return A * np.sin(2 * np.pi * t/T + phi) + k * t + c
    
    # give a estimate value for every dependent variables (in order of sin_model() function)
    p0 = [np.std(y), 365.25, 0.0, 0.0, np.median(y)]
    popt, pcov = curve_fit(sin_model, x, y, p0=p0, maxfev=10000)
    perr = np.sqrt(np.diag(pcov))
    return popt, perr

def predict_sin(t, popt):
    A, T, phi, k, c = popt
    return A * np.sin(2 * np.pi * t/T + phi) + k * t + c

def predict_sin_only(t, popt):
    A, T, phi, k, c = popt
    return A * np.sin(2 * np.pi * t/T + phi)
    
def plot_ts(gw_df, cum_ts, cum_dt, wid, frame_base, 
            gw_x=None, gw_model=None, gw_sin_model=None,   
            cum_x=None, cum_model=None, cum_sin_model=None, 
            cum_unfilt_dt=None, cum_unfilt_ts=None, cum_unfilt_x=None, cum_unfilt_sin_model=None,
            plot_seas_comp=False):
    '''
    Function to plot groundwater and cum displacement ts
    of coords that located within each hdf5 files
    '''

    if not np.isfinite(cum_ts).any():
        return False

    # plot
    if plot_seas_comp:
        fig = plt.figure(figsize=(12, 10), dpi=120)
        gs = fig.add_gridspec(2, 1, height_ratios=[1, 2], hspace=0.05)  # fig.add_gridspec(row_n, column_n); hspace = vertical distance between subplots
        ax_sin = fig.add_subplot(gs[0])
        ax     = fig.add_subplot(gs[1])
    else:
        fig, ax = plt.subplots(figsize=(12, 7), dpi=120)
        ax_sin = None
    # fig, ax = plt.subplots(figsize=(12, 7), dpi=120)
    ax2 = ax.twinx()

    # -------------------------------------------------------------------------------
    # plot if PLOT_SEASON_COMP = True
    if ax_sin is not None:
        # GWL detrend
        if gw_sin_model is not None and gw_x is not None:
            x_dense = np.linspace(gw_x.min(), gw_x.max(), 1000)
            dates_dense = [gw_df['date'].min() + pd.Timedelta(days=float(d)) for d in x_dense]
            ax_sin.plot(dates_dense, predict_sin_only(x_dense, gw_sin_model), color='steelblue', linestyle='-', linewidth=1.2, label='GWL sin comp')

        # GWL detrend
        if cum_sin_model is not None and cum_x is not None:
            x_dense = np.linspace(cum_x.min(), cum_x.max(), 1000)
            dates_dense = [cum_dt[0] + pd.Timedelta(days=float(d)) for d in x_dense]
            ax_sin.plot(dates_dense, predict_sin_only(x_dense, cum_sin_model), color='firebrick', linestyle='-', linewidth=1.2, label='filt CUM sin comp')

        ax_sin.set_title(f'Frame: {frame_base} | Well ID: {wid}', fontsize=12)
        ax_sin.set_ylabel('Seasonal Components', fontsize=12)
        ax_sin.legend(loc='upper right', fontsize=9)
        ax_sin.xaxis.set_major_locator(mdates.YearLocator())
        ax_sin.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        plt.setp(ax_sin.get_xticklabels(), visible=False)
    # -------------------------------------------------------------------------------
    # plot cum.h5
    if cum_unfilt_ts is not None and cum_unfilt_dt is not None:
        sns.scatterplot(
            x=cum_unfilt_dt, y=cum_unfilt_ts, ax=ax, 
            s=30, alpha=0.5, facecolor='lightgrey', edgecolor='grey', linewidth=0.8,
            label='cum.h5')
        
    # sin model
    if cum_unfilt_sin_model is not None and cum_unfilt_x is not None:
        x_dense = np.linspace(cum_unfilt_x.min(), cum_unfilt_x.max(), 1000)
        dates_dense = [cum_unfilt_dt[0] + pd.Timedelta(days=float(d)) for d in x_dense]
        cum_uf_k = cum_unfilt_sin_model[3] * 365.25
        ax.plot(dates_dense, predict_sin(x_dense, cum_unfilt_sin_model), color='grey', linestyle='-', linewidth=1.2, label=f'sin fit: cum.h5 (k = {cum_uf_k:+.2f} mm/yr)')
        cum_unfilt_sin_slope = cum_unfilt_sin_model[3] * x_dense + cum_unfilt_sin_model[4]
        ax.plot(dates_dense, cum_unfilt_sin_slope, color='grey', linestyle='-', linewidth=1.2)

    # -------------------------------------------------------------------------------
    # plot cum_filt_deramp.h5
    sns.scatterplot(
        x=cum_dt, y=cum_ts, ax=ax, 
        s=30, alpha=0.5, facecolor='firebrick', edgecolor='darkred', linewidth=0.8,
        label='cum_filt_deramp.h5')

    # sin model
    if cum_sin_model is not None and cum_x is not None:
        x_dense = np.linspace(cum_x.min(), cum_x.max(), 1000)
        dates_dense = [cum_dt[0] + pd.Timedelta(days=float(d)) for d in x_dense]
        cum_k = cum_sin_model[3] * 365.25
        ax.plot(dates_dense, predict_sin(x_dense, cum_sin_model), color='firebrick', linestyle='-', linewidth=1.2, label=f'sin fit: cum_filt_deramp.h5 (k = {cum_k:+.2f} mm/yr)')
        cum_sin_slope = cum_sin_model[3] * x_dense + cum_sin_model[4]
        ax.plot(dates_dense, cum_sin_slope, color='firebrick', linestyle='-', linewidth=1.2)
        # ax2.text(0.75, 0.88, 
        #         f'$VU_{{sin}} = {A:.2f} \\sin ( \\frac{{2\\pi}}{{{T:.1f}}} t + {phi:.2f}) + {k:.3f} t + {c:.2f}$', 
        #         transform=ax.transAxes, fontsize=9, color='dimgray',
        #         verticalalignment='top')

    # # linear model
    # if cum_model is not None and cum_x is not None:
    #     cum_y_fit = cum_model.predict(sm.add_constant(cum_x))
    #     ax.plot(cum_dt, cum_y_fit, color='black', linestyle='--', linewidth=1.0, label='linear fit: cum_filt_deramp.h5')
    #     # ax.text(0.75, 0.83, f'$VU_{{lin}} = {k:.3f} t + {c:.2f}$',
    #     #          transform=ax.transAxes, fontsize=9, color='black',
    #     #          verticalalignment='top')
    
    # -------------------------------------------------------------------------------
    # plot GWL
    sns.scatterplot(
        x=gw_df['date'], y=gw_df['obs_gw'], ax=ax2, 
        s=30, alpha=0.5, facecolor='steelblue', edgecolor='navy', linewidth=0.8,
        label='Groundwater Level')
    
    # sin model
    if gw_sin_model is not None and gw_x is not None:
        x_dense = np.linspace(gw_x.min(), gw_x.max(), 1000)
        dates_dense = [gw_df['date'].min() + pd.Timedelta(days=float(d)) for d in x_dense]
        gw_k = gw_sin_model[3] * 365.25
        ax2.plot(dates_dense, predict_sin(x_dense, gw_sin_model), color='steelblue', linestyle='-', linewidth=1.2, label=f'sin fit: GWL (k = {gw_k:+.3f} m/yr)')
        gw_sin_slope = gw_sin_model[3] * x_dense + gw_sin_model[4]
        ax2.plot(dates_dense, gw_sin_slope, color='steelblue', linestyle='-', linewidth=1.2)
        # A, T, phi, k, c = gw_sin_model
        # ax2.text(0.75, 0.98, 
        #         f'$GW_{{sin}} = {A:.2f} \\sin ( \\frac{{2\\pi}}{{{T:.1f}}} t + {phi:.2f}) + {k:.3f} t + {c:.2f}$', 
        #         transform=ax2.transAxes, fontsize=9, color='steelblue',
        #         verticalalignment='top')

    # # linear model
    # if gw_model is not None and gw_x is not None:
    #     gw_y_fit = gw_model.predict(sm.add_constant(gw_x))
    #     ax2.plot(gw_df['date'], gw_y_fit, color='navy', linestyle='--', linewidth=1.0, label='linear fit: GWL')
    #     # k, c = gw_model.params[1], gw_model.params[0]
    #     # ax2.text(0.75, 0.93, f'$GW_{{lin}} = {k:.3f} t + {c:.2f}$',
    #     #         transform=ax.transAxes, fontsize=9, color='navy',
    #     #         verticalalignment='top')

    # -------------------------------------------------------------------------------
    # ax settings
    if ax_sin is None:
        ax.set_title(f'Frame: {frame_base} | Well ID: {wid}', fontsize=12)
    ax.set_xlabel('Time', fontsize=12)

    # ax.grid(False)
    ax2.grid(False)

    ax.set_ylabel('Cummulative Displacement (mm)', fontsize=12)
    ax2.set_ylabel('Ground Water Level (m)', color='steelblue', fontsize=12)
    
    ymin, ymax = ax2.get_ylim()
    yrange = ymax - ymin
    ax2.set_ylim(ymin - 0.2*yrange, ymax + 0.2*yrange)
    # gw_centre = np.median(gw_df['obs_gw'].dropna())
    # ax2.set_ylim(gw_centre - 9, gw_centre + 9)
    # if cum_unfilt_ts is not None:
    #     cumF_centre = np.median(cum_ts[~np.isnan(cum_ts)])
    #     cumUF_centre = np.median(cum_unfilt_ts[~np.isnan(cum_unfilt_ts)])
    #     cum_centre = np.mean([cumF_centre, cumUF_centre])
    # else:
    #     cum_centre = np.median(cum_ts[~np.isnan(cum_ts)])
    # ax.set_ylim(cum_centre - 50, cum_centre + 30)

    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

    ax2.ticklabel_format(style='plain', axis='y', useOffset=False)
    ax2.tick_params(axis='y', colors='steelblue')
    ax2.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.2f'))  # keep 2 decimal places 

    # legend setting
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=9)
    ax.get_legend().remove() if ax.get_legend() else None

    plt.savefig(os.path.join(OUT_DIR, f'F{frame_base}_W{wid}.png'))
    # plt.show()
    plt.close(fig)

    return True

def plot_reg(df):
    # convert to float
    gw_vel = df['gw_k_sin'].values.astype(float)
    cum_vel = df['vu_k_sin'].values.astype(float)

    # call WLS fitting
    rel_model = calc_wls(cum_vel, gw_vel)

    if rel_model is not None:
        c = rel_model.params[0]  # intercept
        b = rel_model.params[1]  # slope
        # c_unc = rel_model.bse[0]
        # b_unc = rel_model.bse[1]
    
    print(f'GW change rate = {b:.4f} * vu + {c:.4f}')
    # print(f'  slope b = {b:.4f} +/- {b_unc:.4f}')
    # print(f'  intercept c = {c:.4f} +/- {c_unc:.4f}')
    
    # plot
    plt.figure(figsize=(10, 10), dpi=120)

    plt.axhline(0, color='lightgrey', linewidth=0.8)
    plt.axvline(0, color='lightgrey', linewidth=0.8)

    # plot scatter and errorbar
    # plt.errorbar(cum_vel, gw_vel, xerr=cum_unc, yerr=gw_unc, fmt='none', ecolor='lightgrey', elinewidth=0.8, capsize=2, alpha=0.5)
    sns.scatterplot(data=df, x=cum_vel, y=gw_vel, hue='frame', palette='Set2', edgecolor='dimgray', s=40, alpha=0.7)
    # sns.jointplot(data=wls_pd, x='cum_vel', y='gw_vel', kind='reg', truncate=False)
    
    # plot WLS line
    x_line = np.linspace(cum_vel.min(), cum_vel.max(), 100)
    X_line = sm.add_constant(x_line)
    y_line = rel_model.predict(X_line)

    label_text = f"WLS fit: GW change rate = {b:.4f} * VU + {c:.4f}"
    plt.plot(x_line, y_line, color='darkred', linewidth=1.8, label=label_text)
    plt.legend(fontsize=10)

    plt.xlabel('Vertical velocity (mm/yr)', fontsize=12)
    plt.ylabel('Groundwater Change Rate (m/yr)', fontsize=12)
    plt.title('VU vs Groundwater Change Rate', fontsize=14)

    # save plot
    out_vel_plot = os.path.join(BASE_DIR, 'outputs', 'reg_GWcr_vs_VU.png')
    plt.tight_layout()
    plt.savefig(out_vel_plot)
    plt.show()
    plt.close()
    print(f'GW vs VU scatter saved to {out_vel_plot}.')




if __name__ == '__main__':
    # start
    start = time.time()
    print('\n{} ver{} {} {}'.format(os.path.basename(sys.argv[0]), ver, last_update, author))
    if PLOT_UNFILT:
        print(' --INFO-- PLOT_UNFILT: plotting unfilted cum as well.')
    if PLOT_SEASON_COMP: 
        print(' --INFO-- PLOT_SEASON_COMP: plotting seasonal components.')
    print('----- Start. -----')
    
    # 1) load csv
    df = load_gw_obs_csv(IN_CSV)

    # 2) Wells and groups
    # 2.1 select all wells, and avoid duplicates
    wells = df[['well_id', 'lon', 'lat']].drop_duplicates('well_id')
    print(f'Total {wells.shape[0]} wells found in CSV.')
    
    # group by well_id
    groups = df.groupby('well_id')

    # create a container for wls results
    model_results = []

    # 3) load hdf5 files
    # 3.1 get h5 filenames
    h5_fn = sorted(glob.glob(IN_H5))
    print(f'Total {len(h5_fn)} hdf5 found.')

    well_plotted = 0
    
    # 3.2 loop for each hdf5 file
    for fn in h5_fn:
        frame_base = os.path.basename(fn).split('.cum_filt_deramp.h5')[0]
        print(f'Processing {frame_base} ...')


        # 3.3 load unfiltered cum if toggled on
        cum_unfilt = None
        cum_unfilt_dates = None
        if PLOT_UNFILT:
            print(f'Processing unfilted {frame_base} ...')
            fn_unfilt = fn.replace('.cum_filt_deramp.h5', '.cum.h5')
            if os.path.exists(fn_unfilt):
                with h5.File(fn_unfilt, 'r') as fu:
                    cum_unfilt = fu['cum'][:]
                    imdates_unfilt = fu['imdates'][:]
                cum_unfilt_dates = [datetime.datetime.strptime(str(d), "%Y%m%d") for d in imdates_unfilt]
            else:
                print(f'  Unfiltered h5 not found: {os.path.basename(fn_unfilt)}, skipping.')

        # read in filtered hdf5 file
        with h5.File(fn, 'r') as f:
            frame_plotted = 0

            # get lon and lat values
            lon = get_dim(f, 'lon')
            lat = get_dim(f, 'lat')

            # get vel values
            cum = f['cumU'][:]
            # cum = f['cum'][:]

            # get imdates
            imdates = f['imdates'][:]
            cum_dates = [datetime.datetime.strptime(str(d), "%Y%m%d") for d in imdates]

            # find closest index for each well
            lon_idx = [find_closest_index(lon, lon_x) for lon_x in wells['lon']]
            lat_idx = [find_closest_index(lat, lat_x) for lat_x in wells['lat']]
            # print(df['lon'][:5])
            # print(lon_idx[:5])
            # print(df['lat'][:5])
            # print(lat_idx[:5])

            # 4) Model fitting
            # 4.1 loop each well within this frame
            for wid, xi, yi, lon, lat in zip(wells['well_id'], lon_idx, lat_idx, wells['lon'], wells['lat']):    # zip() to iterate two lists together

                # 4.2 groundwater model fit
                sub = groups.get_group(wid).sort_values('date') # get date for specific well
                gw_ts = sub['obs_gw'].values.astype(float)
                gw_x = (sub['date'] - sub['date'].min()).dt.days.values.astype(float)
                # print(gw_x)
                # print(gw_ts)
                # print(f'Well {wid}: x size = {x_gw.size}, y size = {y_gw.size}')

                # for linear fit
                gw_model = calc_wls(gw_x, gw_ts)
                gw_vel_day, gw_unc_day = gw_model.params[1], gw_model.bse[1]
                # convert gw values from m/day to m/year
                gw_vel = gw_vel_day * 365.25
                gw_unc = gw_unc_day * 365.25

                # for sinusoidal fit
                gw_sin_result = calc_sin(gw_x, gw_ts)
                gw_sin_model, gw_sin_unc = gw_sin_result if gw_sin_result is not None else (None, None)

                # 4.3 cum fit
                xi, yi = int(xi), int(yi)
                cum_ts = cum[:, yi, xi].astype(float)
                cum_x = np.array([(d - cum_dates[0]).days for d in cum_dates], dtype=float)
                # print(cum_x)

                # for linear fit
                cum_model = calc_wls(cum_x, cum_ts)
                if cum_model is not None:
                    cum_vel_day, cum_unc_day = cum_model.params[1], cum_model.bse[1]
                else:
                    continue
                
                # convert gw values from mm/day to mm/year
                cum_vel = cum_vel_day * 365.25
                cum_unc = cum_unc_day * 365.25

                # for sinusoidal fit
                cum_sin_result = calc_sin(cum_x, cum_ts)
                cum_sin_model, cum_sin_unc = cum_sin_result if cum_sin_result is not None else (None, None)

                # 4.4 unfiltered cum (optional)
                cum_unfilt_ts = None
                cum_unfilt_dt = None
                cum_unfilt_x = None
                cum_unfilt_sin_model = None
                cum_unfilt_sin_unc = None
                if cum_unfilt is not None:
                    cum_unfilt_ts = cum_unfilt[:, yi, xi].astype(float)
                    cum_unfilt_x = np.array([(d - cum_unfilt_dates[0]).days for d in cum_unfilt_dates], dtype=float)
                    cum_unfilt_dt = cum_unfilt_dates
                    cum_unfilt_sin_result = calc_sin(cum_unfilt_x, cum_unfilt_ts)
                    cum_unfilt_sin_model, cum_unfilt_sin_unc = cum_unfilt_sin_result if cum_unfilt_sin_result is not None else (None, None)
                
                # convert phi to day-of-year (same convention as InSAR delta_t script)
                if gw_sin_model is not None:
                    doy0_gw = sub['date'].min().timetuple().tm_yday
                    T_gw = gw_sin_model[1]
                    gw_delta_t = (-gw_sin_model[2] * T_gw / (2 * np.pi) + doy0_gw) % 365.25
                    gw_dt_unc = T_gw / (2 * np.pi) * gw_sin_unc[2]
                else:
                    gw_delta_t = np.nan
                    gw_dt_unc = np.nan

                if cum_sin_model is not None:
                    doy0_cum = cum_dates[0].timetuple().tm_yday
                    T_cum = cum_sin_model[1]
                    vu_delta_t = (-cum_sin_model[2] * T_cum / (2 * np.pi) + doy0_cum) % 365.25
                    vu_dt_unc = T_cum / (2 * np.pi) * cum_sin_unc[2]  # 误差传播
                else:
                    vu_delta_t = np.nan
                    vu_dt_unc = np.nan

                # time lag: positive = deformation lags behind GWL
                time_lag = vu_delta_t - gw_delta_t
                if time_lag > 182:
                    time_lag -= 365.25
                elif time_lag < -182:
                    time_lag += 365.25
                time_lag_unc = np.sqrt(vu_dt_unc**2 + gw_dt_unc**2)

                # 6) append model result
                model_results.append({
                    'frame': frame_base,
                    'well_id': wid,
                    'lon': lon,
                    'lat': lat,
                    # linear fit
                    'gw_linear':      gw_vel,
                    'gw_unc_linear':  gw_unc,
                    'vu_linear':      cum_vel,
                    'vu_unc_linear':  cum_unc,
                    # sinusoidal fit: gw  (A in m, phi in rad, k in m/yr)
                    'gw_amp':         gw_sin_model[0]        if gw_sin_model is not None else np.nan,
                    'gw_amp_unc':     gw_sin_unc[0]          if gw_sin_unc   is not None else np.nan,
                    'gw_delta_t':     gw_delta_t,
                    'gw_dt_unc':      gw_dt_unc,
                    'gw_k_sin':       gw_sin_model[3]*365.25 if gw_sin_model is not None else np.nan,
                    'gw_k_sin_unc':   gw_sin_unc[3]*365.25   if gw_sin_unc   is not None else np.nan,
                    # sinusoidal fit: filtered cum  (A in mm, phi in rad, k in mm/yr)
                    'vu_amp':         cum_sin_model[0]        if cum_sin_model is not None else np.nan,
                    'vu_amp_unc':     cum_sin_unc[0]          if cum_sin_unc   is not None else np.nan,
                    'vu_delta_t':     vu_delta_t,
                    'vu_dt_unc':      vu_dt_unc,
                    'vu_k_sin':       cum_sin_model[3]*365.25 if cum_sin_model is not None else np.nan,
                    'vu_k_sin_unc':   cum_sin_unc[3]*365.25   if cum_sin_unc   is not None else np.nan,
                    # phase time lag between gwl and filted vu
                    'time_lag':       time_lag,
                    'time_lag_unc':   time_lag_unc,
                    # sinusoidal fit: unfiltered cum  (A in mm, phi in rad, k in mm/yr)
                    'vu_unfilt_amp':        cum_unfilt_sin_model[0]        if cum_unfilt_sin_model is not None else np.nan,
                    'vu_unfilt_amp_unc':    cum_unfilt_sin_unc[0]          if cum_unfilt_sin_unc   is not None else np.nan,
                    'vu_unfilt_phi':        cum_unfilt_sin_model[2]        if cum_unfilt_sin_model is not None else np.nan,
                    'vu_unfilt_phi_unc':    cum_unfilt_sin_unc[2]          if cum_unfilt_sin_unc   is not None else np.nan,
                    'vu_unfilt_k_sin':      cum_unfilt_sin_model[3]*365.25 if cum_unfilt_sin_model is not None else np.nan,
                    'vu_unfilt_k_sin_unc':  cum_unfilt_sin_unc[3]*365.25   if cum_unfilt_sin_unc   is not None else np.nan,
                })

                # 5) plot
                plotted = plot_ts(sub, cum_ts, cum_dates, wid, frame_base,
                                  gw_x=gw_x, gw_model=gw_model, gw_sin_model=gw_sin_model,
                                  cum_x=cum_x, cum_model=cum_model, cum_sin_model=cum_sin_model,
                                  cum_unfilt_dt=cum_unfilt_dt, cum_unfilt_ts=cum_unfilt_ts,
                                  cum_unfilt_x=cum_unfilt_x, cum_unfilt_sin_model=cum_unfilt_sin_model,
                                  plot_seas_comp=PLOT_SEASON_COMP)
                if plotted:
                    frame_plotted += 1 
                    
            print(f'Frame {frame_base}: plotted {frame_plotted} / {len(wells)} wells.')
            well_plotted = well_plotted + frame_plotted
        
    print(f'total wells plotted {well_plotted} / {len(wells)} wells.')

    # 6.2 export results to csv
    model_pd = pd.DataFrame(model_results)
    out_csv = os.path.join(BASE_DIR, 'data', 'GWLcr_VU_ModelResult.csv')
    model_pd.to_csv(out_csv, index=False)
    print(f'Output csv saved to {out_csv}.')

    # 7) plot GWL change rate vs vu change rate
    # model_df = pd.read_csv(os.path.join(BASE_DIR, 'data', 'GWLcr_VU_ModelResult.csv'))
    plot_reg(model_pd)

    # Finish
    elapsed = time.time() - start
    h = int(elapsed / 3600)
    m = int((elapsed % 3600) / 60)
    s = int(elapsed % 60)
    print('\nElapsed time: {:02}h {:02}m {:02}s'.format(h, m, s))
    print('\n{} successfully finished!\n'.format(os.path.basename(sys.argv[0])))
