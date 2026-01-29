from osgeo import gdal
import matplotlib.pyplot as plt
import numpy as np

ref_tif = gdal.Open('/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/data/vu_shiyang_referenced.tif')
data = ref_tif.GetRasterBand(1).ReadAsArray()
print("shape:", data.shape)

plt.imshow(data)
plt.show()