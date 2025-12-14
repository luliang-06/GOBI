
'''
script to reference InSAR vertical velocity to GPS vertical velocity
using planar ramp inversion.

Inputs: InSAR tif file; GPS file
Outputs: Referenced InSAR tif file
'''

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import warnings
from osgeo import gdal
from shapely.geometry import Point
from shapely.geometry import box

# gdal.UseExceptions()
warnings.filterwarnings("ignore")


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
IN_TIF = os.path.join(BASE_DIR, 'data', 'vu_John_new.tif')
IN_GPS = os.path.join(BASE_DIR, 'data', 'ahbgps_v6pt4_3D_29-Nov-2025_eu.dat')
COORD_EXTEND = (101.7, 37.3, 104.7, 39.3)  # minx, miny, maxx, maxy
OUT_DIR = os.path.join(BASE_DIR, 'outputs')
os.makedirs(OUT_DIR, exist_ok=True)

class OpenTif:
    """ a Class that stores the band array and metadata of a Gtiff file."""
    def __init__(self, filename, sigfile=None, incidence=None, heading=None, N=None, E=None, U=None):
        self.ds = gdal.Open(filename)
        self.basename = os.path.splitext(os.path.basename(filename))[0]
        self.band = self.ds.GetRasterBand(1)
        self.data = self.band.ReadAsArray()
        self.xsize = self.ds.RasterXSize
        self.ysize = self.ds.RasterYSize
        self.left = self.ds.GetGeoTransform()[0]
        self.top = self.ds.GetGeoTransform()[3]
        self.xres = self.ds.GetGeoTransform()[1]
        self.yres = self.ds.GetGeoTransform()[5]
        self.right = self.left + self.xsize * self.xres
        self.bottom = self.top + self.ysize * self.yres
        self.projection = self.ds.GetProjection()
        pix_lin, pix_col = np.indices((self.ds.RasterYSize, self.ds.RasterXSize))
        self.lat, self.lon = self.top + self.yres*pix_lin, self.left+self.xres*pix_col

        # convert 0 and 255 to NaN
        # self.data[self.data==0.] = np.nan
        self.data[self.data==255] = np.nan
        self.data[self.data == -9999] = np.nan
    
    def extract_pixel_value(self, lon, lat, max_width=200):
        x = int((lon - self.left)/self.xres + 0.5)
        y = int((lat - self.top) / self.yres + 0.5)
        # increase window size in steps of 2 until there are non-nan values in the window
        # starting from 2 with 5x5 window because if 1x1 window, stdev will be zero
        # if we use the std of values instead of the corresponding sigma files as stdev
        for n in np.arange(2, max_width+1, 2):
            pixel_values = self.data[y - n: y + n + 1, x - n: x + n + 1]
            index = np.nonzero(~np.isnan(pixel_values))
            if len(index[0]) > 10:
                # print(n, pixel_values)
                break
        pixel_value = np.nanmean(pixel_values)
        stdev = np.nanstd(pixel_values)  # by using nanstd(pixel_values), we are not taking into account the quality of the pixels here.
        return pixel_value, stdev

    def export_tif(self, export_title):
        # Export merged data to tif format.
        driver = gdal.GetDriverByName("GTiff")
        outdata = driver.Create(export_title+'.tif', self.xsize, self.ysize, 1, gdal.GDT_Float32)
        outdata.SetGeoTransform([self.left, self.d1.xres, 0, self.top, 0, self.d1.yres])  ##sets same geotransform as input
        outdata.SetProjection(self.d1.projection)  ##sets same projection as input
        outdata.GetRasterBand(1).WriteArray(self.array)


def load_gps(gps):
    gps_gdf = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    gps_gdf['geometry'] = None
    index = 0
    fl = open(gps, "r").readlines()
    for line in fl:
        if not line.startswith(('lon', '*', "Table")):
            lon, lat, veast_eu, vnorth_eu, vup, seats, snorth, sup, *_ = line.split()
            gps_gdf.loc[index, 'geometry'] = Point(float(lon), float(lat))
            gps_gdf.loc[index, 'vu'] = float(vup)        # up velocity in mm/yr
            gps_gdf.loc[index, 've'] = float(veast_eu)   # eastern velocity in mm/yr
            gps_gdf.loc[index, 'vn'] = float(vnorth_eu)  # northern velocity in mm/yr
            gps_gdf.loc[index, 'se'] = float(seats)      # sigma ve
            gps_gdf.loc[index, 'sn'] = float(snorth)     # sigma vn
            gps_gdf.loc[index, 'su'] = float(sup)        # sigma vu
            
            index += 1

    # liang = './gps/GPS_Liang_etal_2013.csv'
    # fl = open(liang, "r").readlines()
    # for line in fl:
    #     if not line.startswith(('*', "Sta.", ",", " Eurasia", " ITRF2008")):
    #         sta, lon, lat, VN, σvN, VE, σvE, CNE, VU, σvU, Vu, σvu = line.split(',')
    #         if VU != '-':  # only input vertical if Liang as a vertical value
    #             if sta in gps_gdf['station'].values:  # only input vertical if Wang has the same station
    #                 index = gps_gdf.index[gps_gdf['station'] == sta].tolist()[0]  # get index in dataframe based on station
    #                 gps_gdf.loc[index, 'vu'] = float(Vu)  # up velocity in mm/yr relative to stable northern neighbour
    #                 gps_gdf.loc[index, 'su'] = float(σvu)  # sigma vu relative to stable northern neighbour

    return gps_gdf

if __name__ == '__main__':

    ## Open vu tif
    tif = OpenTif(IN_TIF)
    # print(f'tif_John size: {tif.xsize} x {tif.ysize}, resolution: {tif.xres} x {tif.yres}, coord extent: ({tif.left}, {tif.bottom}, {tif.right}, {tif.top})')

    # clip to Shiyang basin extent and save
    tif_shiyang = gdal.Warp(os.path.join(BASE_DIR, 'data', 'vu_shiyang.tif'), IN_TIF, outputBounds=COORD_EXTEND, format="GTiff", dstNodata=-9999)
    tif_shiyang = None  # close the dataset

    # reopen the clipped tif
    tif_shiyang = OpenTif(os.path.join(BASE_DIR, 'data', 'vu_shiyang.tif'))
    # print(f'tif_shiyang size: {tif_shiyang.xsize} x {tif_shiyang.ysize}, resolution: {tif_shiyang.xres} x {tif_shiyang.yres}, coord extent: ({tif_shiyang.left}, {tif_shiyang.bottom}, {tif_shiyang.right}, {tif_shiyang.top})')

    # plot to check
    # plt.imshow(tif.data, vmin=np.nanpercentile(tif.data, 1), vmax=np.nanpercentile(tif.data,99), interpolation='nearest')
    # plt.imshow(tif_shiyang.data, 
    #            extent=(tif_shiyang.left, tif_shiyang.right, tif_shiyang.bottom, tif_shiyang.top), 
    #            vmin=np.nanpercentile(tif_shiyang.data, 1), 
    #            vmax=np.nanpercentile(tif_shiyang.data,99), 
    #            interpolation='nearest')
    # plt.colorbar(label='mm/yr')
    # plt.show()


    ## Load GPS data
    # check data
    gps=pd.read_csv(IN_GPS, delim_whitespace=True)
    # print(gps.head())

    gps=load_gps(IN_GPS)
    gps_shiyang = gpd.clip(gps, box(*COORD_EXTEND))  # clip to Shiyang basin extent
    gps_shiyang.reset_index(drop=True, inplace=True)
    # print(gps_shiyang.head())

    # plot to check
    # fig, ax = plt.subplots(figsize=(10, 10))
    # plt.imshow(tif_shiyang.data, 
    #         extent=(tif_shiyang.left, tif_shiyang.right, tif_shiyang.bottom, tif_shiyang.top), 
    #         vmin=np.nanpercentile(tif_shiyang.data, 1), 
    #         vmax=np.nanpercentile(tif_shiyang.data,99), 
    #         interpolation='nearest')
    # gps_shiyang.plot(ax=ax, c=gps_shiyang['vu'], markersize=60, edgecolor='k') 
    # plt.colorbar(label='mm/yr')
    # plt.show()

    # extract the InSAR vu at gps locations and calculate the difference
    gps_shiyang['insar'] = [tif_shiyang.extract_pixel_value(point.x, point.y, 8)[0] for point in gps_shiyang['geometry']]
    gps_shiyang.dropna(inplace=True)
    gps_shiyang['offset']=gps_shiyang['insar']-gps_shiyang['vu']
    # print(gps_shiyang)
    # gps_shiyang.plot('offset')
    # plt.show()


    ## Planar Ramp Inversion
    x = [int((point.x - tif_shiyang.left) / tif_shiyang.xres + 0.5) for point in gps_shiyang['geometry']]
    y = [int((point.y - tif_shiyang.top) / tif_shiyang.yres + 0.5) for point in gps_shiyang['geometry']]
    offset = gps_shiyang['offset'].to_numpy()

    # design matrix
    G = np.zeros((gps_shiyang.shape[0], 3))
    # populate the design matrix G
    G[:, 0] = y
    G[:, 1] = x
    G[:, 2] = 1
    # Temporarily set print options
    np.set_printoptions(suppress=True)
    # To solve the best fit ramp parameters
        # coefs    = the coefficients output of the linear inversion is the desired model vector. 
        # res      = the smallest sum of squares of residuals obtained. 
        # rank     = rank of the G matrix (3 columns) for 3 model parameters. 
        # singular = the singular values of the G matrix show how strongly that corresponding column of G matrix influences the result. 
    coefs, res, rank, singular = np.linalg.lstsq(G, offset, rcond=None)
    # calc residuals
    model = np.dot(G, coefs)
    residual = offset - model
    rms_offset = np.sqrt(np.mean(offset**2))
    rms_residual = np.sqrt(np.mean(residual**2))
    # print(rms_offset, rms_residual)

    # plot to check the fit
    # fig, ax = plt.subplots(1, 3, sharey='all')

    # im = ax[0].scatter(x, y, c=offset, vmin=-3, vmax=3, marker='o', cmap='RdBu')
    # im = ax[1].scatter(x, y, c=model, vmin=-3, vmax=3, marker='o', cmap='RdBu')
    # im = ax[2].scatter(x, y, c=residual, vmin=-3, vmax=3, marker='o', cmap='RdBu')

    # ax[0].set_title('Offset')
    # ax[1].set_title('Model')
    # ax[2].set_title('Residual')

    # cbar = plt.colorbar(im, ax=ax)
    # cbar.set_label('Offset Value')

    # plt.show()


    ## Placing the InSAR LOS into GPS's reference frame
    # 1. construct a zero matrix of the size of the InSAR raster. 
    ramp_array = np.zeros(tif_shiyang.data.shape)
    # 2. extract the pixel coordinates (row, column) of all pixels as a long 2-column matrix
    all_yx = np.argwhere(~np.isnan(ramp_array))
    # 3. construct a 3-column G matrix that is as long as the number of pixels involved 
    G = np.ones((len(all_yx), 3))
    # 4. populate the first two of the G matrix with the y/x pair of all pixels, leaving the third column as 1 to multiply with the constant parameter c
    G[:, :2] = all_yx
    # 5. calculate the model result and reshape the long vector into the shape of the 2D array, overwriting the original empty 2D array.
    ramp_array = np.dot(G, coefs).reshape(tif_shiyang.ysize, tif_shiyang.xsize)
    # calc referenced insar
    tif_shiyang.data_projected = tif_shiyang.data - ramp_array

    # plot to check
    # fig, ax = plt.subplots(1, 3, sharey='all', figsize=(10, 4))
    # im = ax[0].imshow(tif_shiyang.data, 
    #                   extent=(tif_shiyang.left, tif_shiyang.right, tif_shiyang.bottom, tif_shiyang.top), 
    #                   vmin=np.nanpercentile(tif_shiyang.data_projected, 1), 
    #                   vmax=np.nanpercentile(tif_shiyang.data,99),
    #                   interpolation='nearest')
    # im = ax[1].imshow(ramp_array, 
    #                   extent=(tif_shiyang.left, tif_shiyang.right, tif_shiyang.bottom, tif_shiyang.top), 
    #                   vmin=np.nanpercentile(tif_shiyang.data_projected, 1), 
    #                   vmax=np.nanpercentile(tif_shiyang.data,99), 
    #                   interpolation='nearest')
    # im = ax[2].imshow(tif_shiyang.data_projected, extent=(tif_shiyang.left, tif_shiyang.right, tif_shiyang.bottom, tif_shiyang.top), 
    #                   vmin=np.nanpercentile(tif_shiyang.data_projected, 1), 
    #                   vmax=np.nanpercentile(tif_shiyang.data,99), 
    #                   interpolation='nearest')

    # ax[0].set_title('InSAR LOS')
    # ax[1].set_title('Ramp Model')
    # ax[2].set_title('Referenced LOS')

    # # Adding a color bar to show the mapping of 'offset' to colors
    # cbar = plt.colorbar(im, ax=ax, orientation='horizontal')
    # cbar.set_label('LOS, mm/yr')
    # plt.show()

    # Export referenced insar to tif format.
    driver = gdal.GetDriverByName("GTiff")
    out_tif = tif_shiyang.data_projected
    outdata = driver.Create(os.path.join(BASE_DIR, 'data', 'vu_shiyang_referenced.tif'), out_tif.size, 1, gdal.GDT_Float32)
    outdata.SetGeoTransform([out_tif.left, out_tif.d1.xres, 0, out_tif.top, 0, out_tif.d1.yres])  # sets same geotransform as input
    outdata.SetProjection(out_tif.d1.projection)  # sets same projection as input
    outdata.GetRasterBand(1).WriteArray(out_tif.array)