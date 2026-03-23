
'''
Script to generate a folium interactive html of vu.tif as base and well location as point with timeseries pop up.

Inputs:
data/vu_shiyang.tif
data/GWLcr_VU_ModelResult.csv
outputs/GWL_VU_ts/*.png

Outputs:
outputs/map.html


'''

import os
import folium
import rasterio
import glob
import base64
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# IN_VU = os.path.join(BASE_DIR, 'data', 'vu_John_new.tif')
IN_VU = os.path.join(BASE_DIR, 'data', 'vu_shiyang.tif')
IN_GW = os.path.join(BASE_DIR, 'data', 'GWLcr_VU_ModelResult.csv')
TS_DIR = os.path.join(BASE_DIR, 'outputs', 'GWL_VU_ts')
BOUND = [101.7, 37.3, 104.7, 39.3] # left, bottom, right, top
OUT_DIR = os.path.join(BASE_DIR, 'outputs')

# open tif as baselayer
with rasterio.open(IN_VU) as src:
    bounds = src.bounds
    img = src.read(1)            # read band 1 as numpy array while file is open
    nodata = src.nodata
print('VU loaded succesfully.')

img_masked = np.ma.masked_invalid(img)
img_norm = (np.clip(img_masked, -10, 10) - (-10)) / (10 - (-10))
cmap_vu = plt.get_cmap('RdYlBu_r')
img_rgba = (cmap_vu(img_norm) * 255).astype(np.uint8)
if img_masked.mask is not np.ma.nomask:
    img_rgba[img_masked.mask] = [0, 0, 0, 0]


print(f'nodata: {nodata}')
print(f'img value range: {img.min():.4f} ~ {img.max():.4f}')
print(f'img unique values (sample): {np.unique(img)[:10]}')
print(f'img_rgba alpha range: {img_rgba[:,:,3].min()} ~ {img_rgba[:,:,3].max()}')
print(f'masked pixel count: {img_masked.mask.sum() if img_masked.mask is not np.ma.nomask else 0}')

# load well data
df = pd.read_csv(IN_GW)
df['well_id'] = df['well_id'].astype(str)   # ensure wis as string
print('csv data loaded succesfully.')


# initiate folium map
m = folium.Map(location=[df["lat"].mean(), df["lon"].mean()], 
               tiles='cartodb positron'
               )
m.fit_bounds([[BOUND[1], BOUND[0]], [BOUND[3], BOUND[2]]])  # [[south, west], [north, east]]

# Add vu tif as base layer
folium.raster_layers.ImageOverlay(
    image=img_rgba,
    bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
    opacity=0.7
).add_to(m)

# colormap
cmap = plt.get_cmap('RdYlBu_r')
# vmax = df['gw_k_sin'].max()
# vmin = df['gw_k_sin'].min()
norm = mcolors.TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)

for _, row in df.drop_duplicates(subset=['well_id']).iterrows():
    well_id = row['well_id']
    # vu_str = f'{row['vu_k_sin']:.3f}'
    vu_str = f"{row['vu_k_sin']:.3f}"
    color = mcolors.to_hex(cmap(norm(row['gw_k_sin'])))

    # find matching ts plot by well_id
    matches = glob.glob(os.path.join(TS_DIR, f'*{well_id}*'))
    if matches:
        html = f'<b>Well {well_id}</b><br> VU: {vu_str} mm/y<br>'
        for match in matches:
            with open(matches[0], 'rb') as f:
                img_b64 = base64.b64encode(f.read()).decode('utf-8')
            ext = os.path.splitext(matches[0])[1].lstrip('.')
            html += f'<img src="data:image/{ext};base64,{img_b64}" width="680px"><br>'
    else:
        # html = f'<b>Well {well_id}</b><br>No time series available'
        pass

    popup = folium.Popup(folium.IFrame(html, width=700, height=500), max_width=720)

    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=8, 
        color='dimgray',
        fill=True,
        fill_color=color,
        fill_opacity=0.7,
        weight=1, 
        popup=popup
    ).add_to(m)

# # Add well location as layer
# for _, row in df.iterrows():
#     color = mcolors.to_hex(cmap(norm(row['gw_k_sin'])))
#     folium.CircleMarker(
#         location=[row['lat'], row['lon']],
#         radius=8, 
#         color='dimgray',
#         fill=True,
#         fill_color=color,
#         fill_opacity=0.7,
#         weight=1
#     ).add_to(m)

out_map = os.path.join(OUT_DIR, 'map.html')
m.save(out_map)
print('Finished.')