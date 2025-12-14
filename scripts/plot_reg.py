
'''
Script to plot regression between GW change rate and VU

Inputs: gw_vel.csv; VU.tif
Outputs: GW_vel_VU.png
'''

import os 
import numpy as np
import seaborn as sns
import statsmodels.api as sm
import matplotlib.pyplot as plt
from scripts.plot_ts import calc_wls, wls_pd


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
IN_CSV = os.path.join(BASE_DIR, 'data', '2018-2022_ShiyangBasin_Groundwater_WaterLevel_FIXED.csv')
IN_H5 = os.path.join(BASE_DIR, 'data', '*.cum_filt_deramp.h5')
OUT_DIR = os.path.join(BASE_DIR, 'outputs', 'GW_cum_fdU_ts')
os.makedirs(OUT_DIR, exist_ok=True)

# plot settings
sns.set_theme(style="whitegrid", context="talk", rc={"grid.linewidth": 0.8})
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['xtick.labelsize'] = 12
plt.rcParams['ytick.labelsize'] = 12

if __name__ == '__main__':
    # 6) plot gw_vel vs cum_vel
    # 6.1 convert to float
    gw_vel = wls_pd['gw_vel'].values.astype(float)
    cum_vel = wls_pd['cum_vel'].values.astype(float)

    # 6.2 call WLS fitting
    rel_model = calc_wls(cum_vel, gw_vel)

    if rel_model is not None:
        c = rel_model.params[0]  # intercept
        b = rel_model.params[1]  # slope
        # c_unc = rel_model.bse[0]
        # b_unc = rel_model.bse[1]
    
    print(f'gw_vel = {b:.4f} * cum_vel + {c:.4f}')
    # print(f'  slope b = {b:.4f} +/- {b_unc:.4f}')
    # print(f'  intercept c = {c:.4f} +/- {c_unc:.4f}')
    
    # 6.3 plot
    plt.figure(figsize=(10, 10), dpi=120)

    plt.axhline(0, color='lightgrey', linewidth=0.8)
    plt.axvline(0, color='lightgrey', linewidth=0.8)

    # plot scatter and errorbar
    # plt.errorbar(cum_vel, gw_vel, xerr=cum_unc, yerr=gw_unc, fmt='none', ecolor='lightgrey', elinewidth=0.8, capsize=2, alpha=0.5)
    sns.scatterplot(data=wls_pd, x='cum_vel', y='gw_vel', hue='frame', palette='Set2', edgecolor='dimgray', s=40, alpha=0.7)
    # sns.jointplot(data=wls_pd, x='cum_vel', y='gw_vel', kind='reg', truncate=False)
    
    # plot WLS line
    x_line = np.linspace(cum_vel.min(), cum_vel.max(), 100)
    X_line = sm.add_constant(x_line)
    y_line = rel_model.predict(X_line)

    label_text = f"WLS fit: gw_vel = {b:.4f} * cum_vel + {c:.4f}"
    plt.plot(x_line, y_line, color='darkred', linewidth=1.8, label=label_text)
    plt.legend(fontsize=10)

    plt.xlabel('cumU velocity (mm/yr)', fontsize=12)
    plt.ylabel('groundwater velocity (m/yr)', fontsize=12)
    plt.title('cumU vel vs groundwater vel', fontsize=14)

    # 6.4 save plot
    out_vel_plot = os.path.join(BASE_DIR, 'outputs', 'GWvsCumU_vel.png')
    plt.tight_layout()
    plt.savefig(out_vel_plot)
    plt.show()
    plt.close()
    print(f'GW vs Cum velocity scatter saved to {out_vel_plot}.')