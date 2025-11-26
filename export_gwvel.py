import rasterio
import numpy as np

vu_file = '/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/data/vu_qi.tif'
gw_vel_tif = '/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/outputs/gw_vel.tif'


with rasterio.open(vu_file) as src:
    vu = src.read(1).astype("float32")
    profile = src.profile.copy()
    nodata = src.nodata

    gw_vel = b * vu + c
    gw_vel = gw_vel.astype("float32")

    profile_gw = profile.copy()
    profile_gw.update(dtype="float32", nodata=nodata, count=1)

    with rasterio.open(gw_vel_tif, "w", **profile_gw) as dst:
        dst.write(gw_vel, 1)