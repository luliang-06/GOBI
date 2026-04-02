#!/usr/bin/env python3
'''
Written by Lu Liang, University of Edinburgh, School of Geosciences, 2026.

===========
Description
===========
Script to plot a tif for check.

============
Inputs Files
============
data/
    *.tif

============
Output Files
============
'''
# Change Log
'''
v1.0 20260126, Lu Liang, UoE
'''

import os
import sys
import time
import numpy as np
from osgeo import gdal
import matplotlib.pyplot as plt

author = 'Lu Liang, University of Edinburgh, School of Geosciences'
ver = 'v1.0'
last_update = '2026-01-26'

# Start
start = time.time()
print('\n{} ver{} {} {}'.format(os.path.basename(sys.argv[0]), ver, last_update, author))

ref_tif = gdal.Open('/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/frames/033D_05106_131313/TS_GEOCml1GACOS/cum_filt.h5_amp.tif')
data = ref_tif.GetRasterBand(1).ReadAsArray()
print("shape:", data.shape)

plt.imshow(data)
plt.show()

# Finish
elapsed = time.time() - start
h = int(elapsed / 3600)
m = int((elapsed % 3600) / 60)
s = int(elapsed % 60)
print('\nElapsed time: {:02}h {:02}m {:02}s'.format(h, m, s))
print('\n{} successfully finished!\n'.format(os.path.basename(sys.argv[0])))