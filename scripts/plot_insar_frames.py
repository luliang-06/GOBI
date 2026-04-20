#!/usr/bin/env python3
'''
Written by Lu Liang, University of Edinburgh, School of Geosciences, 2025.

===========
Description
===========
This script use pyGMT to plot LiCSBAS frame on hillsahde.

============
Inputs Files
============
data/
    vu_AHB.tif

============
Output Files
============
outputs/
    frames_on_hillshade.png
'''
# Change Log
'''
v1.0 20260419, Lu Liang, UoE
 - script wrriten.
'''

import os
import numpy as np
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape
from shapely.ops import unary_union
import pygmt
# from skimage import measure

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SY_BOUNDARY = "/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/data/wuwei_level5_basin.gmt"
FRAME_DIRS = [
    # "/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/frames/128A_05172_131313/",
    # "/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/frames/055A_05021_131313/",
    # "/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/frames/055A_05221_131313/",
    "/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/frames/033D_05106_131313/",
    "/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/frames/135D_05023_131313/",
    "/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/frames/135D_05222_131313/",

]
FRAME_LABELS = ["033D_05106_131313", "135D_05023_131313", "135D_05222_131313", "128A_05172_131313", "055A_05021_131313", "055A_05221_131313"]
FRAME_COLORS = [
    # "220/50/50",
    # "220/50/50",
    # "220/50/50",
    "50/100/200",
    "50/100/200",
    "50/100/200",
]
REGION = [99.75, 105.75, 36.25, 41.25]
MAP_WIDTH = "12c"
DEM_RESOLUTION = "03s"  # SRTM resolution: "01m"=~1.8km, "03s"=~90m, "01s"=~30m
PEN_WIDTH = "1.0p"

OUT_DIR = os.path.join(BASE_DIR, 'outputs', 'frames_on_hillshade_d.png')


def mli_boundary_polygon(frame_dir: str, simplify_tol: float = 0.01):
    frame_id = os.path.basename(frame_dir.rstrip("/"))
    tif_path = os.path.join(frame_dir, f"{frame_id}.geo.mli.tif")
    with rasterio.open(tif_path) as src:
        data = src.read(1)
        mask = (data > 0).astype(np.uint8)
        polys = [shape(geom) for geom, val in shapes(mask, transform=src.transform) if val == 1]

    boundary = unary_union(polys).simplify(simplify_tol)
    if boundary.geom_type == 'MultiPolygon':
        boundary = max(boundary.geoms, key=lambda p: p.area)
    lons, lats = boundary.exterior.coords.xy
    return list(lons), list(lats)


if __name__ == "__main__":

    # 1. Resolve frame labels
    labels = FRAME_LABELS if FRAME_LABELS else [os.path.basename(d) for d in FRAME_DIRS]

    # 2. Parse slc.mli boundaries
    polygons = []
    for d in FRAME_DIRS:
        frame_id = os.path.basename(d.rstrip("/"))
        tif = os.path.join(d, f"{frame_id}.geo.mli.tif")
        if not os.path.exists(tif):
            raise FileNotFoundError(f"Cannot find {frame_id}.geo.mli.tif in: {d}")
        lons, lats = mli_boundary_polygon(d)
        polygons.append((lons, lats))

    # 3. Download SRTM DEM
    print(f"Downloading SRTM {DEM_RESOLUTION} DEM for region {REGION} ...")
    dem = pygmt.datasets.load_earth_relief(
        resolution=DEM_RESOLUTION,
        region=REGION,
    )

    # 4. Compute hillshade
    print("Computing hillshade gradient ...")
    gradient = pygmt.grdgradient(dem, azimuth=315, normalize="e0.6")

    # 5. Build figure
    fig = pygmt.Figure()

    # Hillshade base
    pygmt.makecpt(cmap="gray", series=[dem.values.min(), dem.values.max()])
    fig.grdimage(
        dem,
        projection=f"M{MAP_WIDTH}",
        region=REGION,
        shading=gradient,
        cmap=True,
    )

    # Draw Shiyang Boundary
    fig.plot(
        data=SY_BOUNDARY,
        region=REGION,
        projection=f"M{MAP_WIDTH}",
        pen="1.5p,white",
        label="Study area+s0.2c",
    )
    # 6. Draw frame polygons
    for i, ((lons, lats), label, color) in enumerate(
        zip(polygons, labels, FRAME_COLORS)
    ):
        import pandas as pd
        df = pd.DataFrame({"lon": lons, "lat": lats})

        fig.plot(
            x=df["lon"],
            y=df["lat"],
            region=REGION,
            projection=f"M{MAP_WIDTH}",
            pen=f"{PEN_WIDTH},{color}",
            label=f"{label}+s0.25c",
        )

    # 7. Frame, gridlines, tick labels
    fig.basemap(
        region=REGION,
        projection=f"M{MAP_WIDTH}",
        frame=[
            "ESne",                       # tick labels on West + South
            "xa1f0.25g1",             # lon: annotate every 0.5°, grid every 0.5°
            "ya1f0.25g1",             # lat: same
        ],
    )

    # 9. Save
    print(f"Saving {OUT_DIR} (dpi=300) ...")
    fig.savefig(OUT_DIR, dpi=300)

    print("Done.")
