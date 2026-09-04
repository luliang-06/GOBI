#!/usr/bin/env python3
'''
Written by Lu Liang, University of Edinburgh, School of Geosciences, 2026.

===========
Description
===========
A toolkit to save the time series used from plot_ts_new.


'''
# Change Log:
'''
v1.0 20260902, LuLiang, UoE
 - initial version
'''

import os
import datetime
import h5py as h5
import numpy as np
import pandas as pd


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

def extract_ts(wells, h5_files, dataset='cumU', out_dir=None):
    ts = []

    for fn in h5_files:
        frame_base = os.path.basename(fn).split('.cum')[0]

        with h5.File(fn, 'r') as f:
            lon = get_dim(f, 'lon')
            lat = get_dim(f, 'lat')
            width = len(lon)

            imdates = f['imdates'][:]
            dates = [datetime.datetime.strptime(str(d), "%Y%m%d") for d in imdates]

            cum = f[dataset]

            for wid, wlon, wlat in zip(wells['well_id'], wells['lon'], wells['lat']):
                xi = int(find_closest_index(lon, wlon))
                yi = int(find_closest_index(lat, wlat))
                pixel_index = yi * width + xi
                pixel_ts = cum[:, yi, xi].astype(float)

                for d, v in zip(dates, pixel_ts):
                    ts.append({
                        'well_id': wid, 
                        'frame': frame_base, 
                        'lon_idx': xi, 
                        'lat_idx': yi,
                        'pixel_index': pixel_index,
                        'date': d, 
                        dataset: v
                    })

    ts_df = pd.DataFrame(ts)

    if out_dir is not None:
        os.makedirs(out_dir, exist_ok=True)
        ts_df.to_csv(os.path.join(out_dir, 'InSAR_timeseries.csv'), index=False)

    return ts_df