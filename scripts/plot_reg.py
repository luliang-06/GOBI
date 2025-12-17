
'''
Script to plot regression between GW change rate and VU

Inputs: gw_vel.csv; VU.tif
Outputs: GW_vel_VU.png
'''

import os 
import numpy as np
import pandas as pd
import seaborn as sns
import geopandas as gpd
import matplotlib.pyplot as plt
import statsmodels.api as sm

from plot_ts import load_gw_obs_csv, calc_wls
from gps_reference import OpenTif


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
IN_GW = os.path.join(BASE_DIR, 'data', '2018-2022_ShiyangBasin_Groundwater_WaterLevel_FIXED.csv')
IN_VU = os.path.join(BASE_DIR, 'data', 'vu_shiyang_referenced.tif')
OUT_DIR = os.path.join(BASE_DIR, 'outputs')
os.makedirs(OUT_DIR, exist_ok=True)   

# plot settings
sns.set_theme(style="whitegrid", context="talk", rc={"grid.linewidth": 0.8})
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['xtick.labelsize'] = 12
plt.rcParams['ytick.labelsize'] = 12



gw_df = load_gw_obs_csv(IN_GW)
# print(gw_df.head)

# convert gw dataframe to geodataframe
gw_gdf = gpd.GeoDataFrame(gw_df, geometry=gpd.points_from_xy(gw_df['lon'], gw_df['lat']), crs='EPSG:4326')
# print(gw_gdf.head)

groups = gw_gdf.groupby('well_id')

gw_gdf['gw_vel'] = np.nan
gw_gdf['gw_vel_unc'] = np.nan

for wid, sub in groups:
    sub = sub.sort_values('date')
    gw_ts = sub['obs_gw'].values.astype(float)
    gw_x  = (sub['date'] - sub['date'].min()).dt.days.values.astype(float)

    gw_model = calc_wls(gw_x, gw_ts)
    gw_vel_day, gw_unc_day = gw_model.params[1], gw_model.bse[1]

    # convert gw values from m/day to m/year
    gw_vel = gw_vel_day * 365.25
    gw_unc = gw_unc_day * 365.25

    # append results in gw_gdf
    mask = gw_gdf['well_id'] == wid
    gw_gdf.loc[mask, 'gw_vel'] = gw_vel
    gw_gdf.loc[mask, 'gw_vel_unc'] = gw_unc

# Open vu tif
vu_tif = OpenTif(IN_VU)

# extract vu value at well location
vals = gw_gdf.geometry.apply(lambda pt: vu_tif.extract_pixel_value(pt.x, pt.y, 8))
gw_gdf[['vu', 'vu_sd']] = pd.DataFrame(vals.tolist(), index=gw_gdf.index)

# print to check
print(gw_gdf[['well_id','lon','lat', 'vu','vu_sd']].drop_duplicates().head(10))

# plot 
gw_vel = gw_gdf['gw_vel'].values.astype(float)
cum_vel = gw_gdf['vu'].values.astype(float)

rel_model = calc_wls(cum_vel, gw_vel)

if rel_model is not None:
    c = rel_model.params[0]  # intercept
    b = rel_model.params[1]  # slope
    # c_unc = rel_model.bse[0]
    # b_unc = rel_model.bse[1]

print(f'gw_vel = {b:.4f} * vu + {c:.4f}')

plt.figure(figsize=(8, 8), dpi=120)
sns.scatterplot(data=gw_gdf, x='vu', y='gw_vel', color='#6cabeb', edgecolor='dimgray', linewidth=0.4, s=50, alpha=0.35)

x_line = np.linspace(gw_gdf['vu'].min(), gw_gdf['vu'].max(), 100)
X_line = sm.add_constant(x_line)
y_line = rel_model.predict(X_line)

label_text = f"WLS fit: GW change rate = {b:.4f} * VU + {c:.4f}"
plt.plot(x_line, y_line, color='darkred', linewidth=1.8, label=label_text)
plt.legend(fontsize=12)

plt.xlabel('Vertical velocity (mm/yr)', fontsize=12)
plt.ylabel('groundwater change rate (m/yr)', fontsize=12)
plt.title('VU vs groundwater Change Rate', fontsize=14)

# save plot
out_vel_plot = os.path.join(BASE_DIR, 'outputs', 'GW_vs_JohnVU_.png')
plt.tight_layout()
plt.savefig(out_vel_plot)
plt.close()
print(f'GW vs Cum velocity scatter saved to {out_vel_plot}.')
