import rasterio
import numpy as np

vu_file = '/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/data/vu_AHB.tif'
# vu_file = '/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/data/vu_Qi_fillnodata.tif'
gw_vel_tif = '/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/data/gwl_cr_all.tif'


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