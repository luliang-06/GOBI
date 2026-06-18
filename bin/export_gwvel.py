#!/usr/bin/env python3
'''
Written by Lu Liang, University of Edinburgh, School of Geosciences, 2025.

===========
Description
===========
This script apply regression function to vu,
transfer vu (mm/yr) to predict gwl change rate (m/yr).

============
Inputs Files
============
data/
    vu_AHB.tif

============
Output Files
============
data/
    gwl_cr_all.tif
'''
# Change Log
'''
v1.0 20251126, Lu Liang, UoE
 - script wrriten.
'''

import os
import sys
import time
import rasterio
import numpy as np

author = 'Lu Liang, University of Edinburgh, School of Geosciences'
ver = 'v1.0'
last_update = '2025-11-26'


vu_file = '/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/outputs/gps_ref/vu_shiyang_referenced.tif'
# vu_file = '/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/data/vu_Qi_fillnodata.tif'
gw_vel_tif = '/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/data/gwl_cr_SYref.tif'

# Start    
start = time.time()
print('\n{} ver{} {} {}'.format(os.path.basename(sys.argv[0]), ver, last_update, author))

with rasterio.open(vu_file) as src:
    vu = src.read(1).astype("float32")
    profile = src.profile.copy()
    nodata = src.nodata
    if nodata == None:
        nodata = -9999.0
    mask = (vu == nodata) | np.isnan(vu)


    gw_vel = 0.0469 * vu -0.1266
    gw_vel = gw_vel.astype("float32")
    gw_vel[mask] = nodata

    profile_gw = profile.copy()
    profile_gw.update(dtype="float32", nodata=nodata, count=1)

    with rasterio.open(gw_vel_tif, "w", **profile_gw) as dst:
        dst.write(gw_vel, 1)

# Finish
elapsed = time.time() - start
h = int(elapsed / 3600)
m = int((elapsed % 3600) / 60)
s = int(elapsed % 60)
print('\nElapsed time: {:02}h {:02}m {:02}s'.format(h, m, s))
print('\n{} successfully finished!\n'.format(os.path.basename(sys.argv[0])))