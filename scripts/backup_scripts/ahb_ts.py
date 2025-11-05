#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 17 16:54:52 2025

@author: eejap
"""

import datetime
import h5py as h5
import numpy as np
import matplotlib.pyplot as plt

#%% plot time series

lat1, lon1 = 35.844, 50.806
lat2, lon2 = 36.008, 50.924
lat3, lon3 = 36.005, 50.496
lat4, lon4 = 36.095, 50.217

asc_h5 = '/nfs/a285/homes/eejap/ahb_vels/figures/subsidence/035D_05397_131013.cum.h5'

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

# open hdf5 file:
h5_file = h5.File(asc_h5, 'r')
# get lat and lon values:
lat = get_dim(h5_file, 'lat')
lon = get_dim(h5_file, 'lon')
# meshgrid the lat and lon values:
grid_lon, grid_lat = np.meshgrid(lon, lat)
# get velocity values:
cum = h5_file['cum'][:]
# get imdates
imdates = h5_file['imdates'][:]

lat_index1 = find_closest_index(lat, lat1)
lon_index1 = find_closest_index(lon, lon1)

lat_index2 = find_closest_index(lat, lat2)
lon_index2 = find_closest_index(lon, lon2)

lat_index3 = find_closest_index(lat, lat3)
lon_index3 = find_closest_index(lon, lon3)

lat_index4 = find_closest_index(lat, lat4)
lon_index4 = find_closest_index(lon, lon4)

# Access the cumulative displacement value at the desired latitude and longitude
cumulative_displacement_1 = cum[:, lat_index1, lon_index1]
cumulative_displacement_2 = cum[:, lat_index2, lon_index2]
cumulative_displacement_3 = cum[:, lat_index3, lon_index3]
cumulative_displacement_4 = cum[:, lat_index4, lon_index4]

# convert dates to datetime
datetime_dates = [datetime.datetime.strptime(str(date), "%Y%m%d") for date in imdates]

plt.figure(figsize=(10, 3.5))

plt.tick_params(axis='x', direction='in', length=4, top=True)
plt.tick_params(axis='y', direction='in', length=4, top=True)

plt.plot(datetime_dates, cumulative_displacement_1, color = 'tab:blue')
plt.plot(datetime_dates, cumulative_displacement_2, color = 'tab:purple')
plt.plot(datetime_dates, cumulative_displacement_3, color = 'tab:orange')
plt.plot(datetime_dates, cumulative_displacement_4, color = 'tab:olive')
plt.ylabel('Cumulative displacement (mm)')


plt.savefig('/nfs/see-fs-02_users/eejap/public_html/plots/ahb_ts.png', dpi = 300)