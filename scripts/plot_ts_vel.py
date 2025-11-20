
'''
Tidy version of plot_displacement_ts.py

Editor: Lu
Update: 15 Oct 2025 - read in gw data and hdf5 file correclty
Update: 28 Oct 2025 - plot ts of cum and ground water for specific well
Update: 6  Nov 2025 - output plots path added.
Update: 15 Nov 2025 - WLS fitting function added; plot function updated to show gw AND cum.
Update: 17 Nov 2025 - plot functions updated to avoid duplicate loops.
Update: 19 Nov 2025 - WLS fitting function applied and export to csv; plot_ts function updated to add plots of wls results.
Update: 19 Nov 2025 - vel plot function added
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

    # print(f'WLS slope: {wls2_result.params[1]:.6f} +/- {wls2_result.bse[1]:.6f}')
    return wls2_result


def plot_ts(gw_df, cum_ts, cum_dt, wid, frame_base, 
            gw_model=None, gw_x=None, 
            cum_model=None, cum_x=None):
    '''
    Function to plot groundwater and cum displacement ts
    of coords that located within each hdf5 files
    '''

    if not np.isfinite(cum_ts).any():
        return False

    # plot
    fig, ax = plt.subplots(figsize=(12, 7), dpi=50)
    ax2 = ax.twinx()

    # plot groundwater level
    sns.scatterplot(
        x=gw_df['date'], y=gw_df['obs_gw'], ax=ax, 
        s=50, alpha=0.5, facecolor='steelblue', edgecolor='navy', linewidth=0.8,
        label='Ground Water Level', legend=False
    )

    # plot cummulative displacement
    sns.scatterplot(
        x=cum_dt, y=cum_ts, ax=ax2, 
        s=50, alpha=0.5, facecolor='grey', edgecolor='dimgray', linewidth=0.8,
        label='Cum displacement', legend=False
    )

    # plot wls result
    # gw
    if (gw_model is not None) and (gw_x is not None):
        gw_y_fit = gw_model.predict(sm.add_constant(gw_x))
        ax.plot(gw_df['date'], gw_y_fit, color='darkblue', linestyle='--', linewidth=1.5)
    # cum
    if (cum_model is not None) and (cum_x is not None):
        cum_y_fit = cum_model.predict(sm.add_constant(cum_x))
        ax2.plot(cum_dt, cum_y_fit, color='black', linestyle='--', linewidth=1.5)


    # ax settings
    ax.set_title(f'Well ID: {wid} Frame: {frame_base}', fontsize=12)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Ground Water Level (m)', fontsize=12)
    ax2.set_ylabel('LOS Displacement (mm)', fontsize=12)
    ax.grid(linestyle='--', alpha=0.5, color='steelblue')

    ymin, ymax = ax.get_ylim()
    yrange = ymax - ymin
    ax.set_ylim(ymin - 0.05*yrange, ymax + 0.05*yrange)
    # keep 2 decimal places 
    ax.ticklabel_format(style='plain', axis='y', useOffset=False)
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.2f'))

    plt.savefig(os.path.join(OUT_DIR, f'F{frame_base}_W{wid}.png'))
    # plt.show()
    plt.close(fig)

    return True



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

    # 2) Wells and groups
    # 2.1 select all wells, and avoid duplicates
    wells = df[['well_id', 'lon', 'lat']].drop_duplicates('well_id')
    print(f'Total {wells.shape[0]} wells found in CSV.')
    
    # group by well_id
    groups = df.groupby('well_id')

    # create a container for wls results
    wls_results = []


    # 3) load hdf5 files
    # 3.1 get h5 filenames
    h5_fn = sorted(glob.glob(IN_H5))
    print(f'Total {len(h5_fn)} hdf5 found.')

    # 3.2 loop for each hdf5 file
    for fn in h5_fn:
        frame_base = os.path.basename(fn).split('.cum_filt.h5')[0]
        print(f'Processing {frame_base} ...')

        frame_plotted = 0

        # read in hdf5 file
        with h5.File(fn, 'r') as f:

            # get lon and lat values
            lon = get_dim(f, 'lon')
            lat = get_dim(f, 'lat')

            # get vel values
            cum = f['cum'][:]

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

            # 4) WLS fitting
            # 4.1 loop each well within this frame
            for wid, xi, yi, lon, lat in zip(wells['well_id'], lon_idx, lat_idx, wells['lon'], wells['lat']):    # zip() to iterate two lists together

                # 4.2 groundwater WLS
                sub = groups.get_group(wid).sort_values('date') # get date for specific well
                gw_ts = sub['obs_gw'].values.astype(float)
                gw_x = (sub['date'] - sub['date'].min()).dt.days.values.astype(float)
                # print(f'Well {wid}: x size = {x_gw.size}, y size = {y_gw.size}')
                gw_model = calc_wls(gw_x, gw_ts)
                gw_vel, gw_unc = gw_model.params[1], gw_model.bse[1]

                # gw_vel = gw_vel_m * 1000
                # gw_unc = gw_unc_m * 1000

                # 4.3 cum WLS
                xi, yi = int(xi), int(yi)
                cum_ts = cum[:, yi, xi].astype(float)
                cum_x = np.array([(d - cum_dates[0]).days for d in cum_dates], dtype=float)
                cum_model = calc_wls(cum_x, cum_ts)
                if cum_model is not None:
                    cum_vel, cum_unc = cum_model.params[1], cum_model.bse[1]
                else:
                    continue

                # 4.4 store reults
                wls_results.append({
                    'frame': frame_base,
                    'well_id': wid,
                    'lon': lon,
                    'lat': lat,
                    'gw_vel': gw_vel,
                    'gw_unc': gw_unc,
                    'cum_vel': cum_vel,
                    'cum_unc': cum_unc
                })

                # 5) plot
                # plotted = plot_ts(sub, cum_ts, cum_dates, wid, frame_base, gw_model, gw_x, cum_model, cum_x)
                # if plotted:
                #     frame_plotted += 1 

        # print(f'Frame {frame_base}: plotted {frame_plotted} / {len(wells)} wells.')

    # 4.5 export wls results to csv
    wls_pd = pd.DataFrame(wls_results)
    out_csv = os.path.join(BASE_DIR, 'data', 'gw_cum_wls.csv')
    wls_pd.to_csv(out_csv, index=False)
    print(f'Output csv saved to {out_csv}.')

    # 6) plot gw_vel vs cum_vel
    # 6.1 get valid data
    valid = wls_pd.dropna(subset=['gw_vel', 'cum_vel'])
    gw_v = valid['gw_vel'].values.astype(float)
    cum_v = valid['cum_vel'].values.astype(float)

    # 6.2 plot velocity scatter
    plt.figure(figsize=(6, 6), dpi=100)
    plt.errorbar(cum_v, gw_v, xerr=cum_unc, yerr=gw_unc, fmt='none', ecolor='grey', elinewidth=1, capsize=2, alpha=0.7)
    sns.scatterplot(x=cum_v, y=gw_v, s=60, color='steelblue', edgecolor='navy', alpha=0.9)

    plt.axhline(0, color='lightgrey', linewidth=0.8)
    plt.axvline(0, color='lightgrey', linewidth=0.8)

    plt.xlabel('Cum velocity (mm/yr)', fontsize=12)
    plt.ylabel('GW velocity (m/yr)', fontsize=12)
    plt.title('Cum velocity vs GW velocity', fontsize=14)

    # 6.3 call WLS fitting
    rel_model = calc_wls(cum_v, gw_v)

    if rel_model is not None:
        c = rel_model.params[0]  # 截距
        b = rel_model.params[1]  # 斜率
        # c_unc = rel_model.bse[0]
        # b_unc = rel_model.bse[1]
    
    print(f'cum_vel = {b:.4f} * gw_vel + {c:.4f}')
    # print(f'  slope b = {b:.4f} +/- {b_unc:.4f}')
    # print(f'  intercept c = {c:.4f} +/- {c_unc:.4f}')
    
    # 6.4 plot WLS line
    x_line = np.linspace(gw_v.min(), gw_v.max(), 100)
    X_line = sm.add_constant(x_line)
    y_line = rel_model.predict(X_line)

    label_text = f"WLS fit: cum_vel = {b:.4f} * gw_vel + {c:.4f}"
    plt.plot(x_line, y_line, color='darkred', linewidth=1.8, label=label_text)
    plt.legend(fontsize=12)

    # 6.5 save plot
    out_vel_plot = os.path.join(BASE_DIR, 'outputs', 'gw_cum_vel_scatter.png')
    plt.tight_layout()
    plt.savefig(out_vel_plot)
    plt.show()
    plt.close()
    print(f'GW vs Cum velocity scatter saved to {out_vel_plot}.')
    
    print('Finished')
