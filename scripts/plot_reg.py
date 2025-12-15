
'''
Script to plot regression between GW change rate and VU

Inputs: gw_vel.csv; VU.tif
Outputs: GW_vel_VU.png
'''

import os 
import numpy as np
import seaborn as sns
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point
from scripts.gps_reference import OpenTif


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
IN_GW = os.path.join(BASE_DIR, 'data', 'gw_cum_wls_FIXED.csv')
IN_VU = os.path.join(BASE_DIR, 'data', 'vu_John_new.tif')
OUT_DIR = os.path.join(BASE_DIR, 'outputs')
os.makedirs(OUT_DIR, exist_ok=True)

# plot settings
sns.set_theme(style="whitegrid", context="talk", rc={"grid.linewidth": 0.8})
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['xtick.labelsize'] = 12
plt.rcParams['ytick.labelsize'] = 12

def load_gdf(in_file):
    gdf = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    gdf['geometry'] = None
    index = 0
    fl = open(in_file, "r").readlines()
    for line in fl:
        frame, well_id, lon, lat, gw_vel, gw_unc, cum_vel, cum_unc = line.split()
        gdf.loc[index, 'geometry'] = Point(float(lon), float(lat))
        gdf.loc[index, 'well_id'] = well_id[:]
     

if __name__ == '__main__':
    # read in gw table
    gw_gdf = load_gdf(IN_GW)
    
    # Open vu tif

    # extract vu value at well location