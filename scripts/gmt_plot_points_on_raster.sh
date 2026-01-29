#!/usr/bin/env bash
gmt set MAP_FRAME_TYPE plain 
gmt set PS_MEDIA a4
gmt set FONT_ANNOT_PRIMARY 8
gmt set FONT_LABEL 8
gmt set FORMAT_GEO_MAP D
gmt set FONT_TITLE 16p
gmt set MAP_TICK_LENGTH_PRIMARY 2p 
gmt set MAP_ANNOT_OFFSET_PRIMARY 1.25p
gmt set MAP_LABEL_OFFSET 2p
gmt set MAP_ANNOT_OFFSET_SECONDARY auto


raster=/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/outputs/gw_vel_all.nc # path to a raster file

# echo "lon lat rate 
# 70 40 1.2
# 80 48 -2.1" > points.txt 
points=/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/data/gw_cum_wls_FIXED.csv # or a separate txt file (if comma delimited, you'll need to change the awk statement below slightly)

gmt begin points_on_raster png,pdf
	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn  # draw the map frame, change the boundary to -Rleft/right/bottom/top -B5 for a grid tick every 5 degrees, play with how you capitalise wesn after the second -B
    gmt makecpt -Croma -T-1/1 -I # change the limits of your colour map
	gmt grdimage $raster -n+c -Q 
    gmt colorbar -DjTL+w1.8/13%+o1/1+h+e+ml -Bx1+l"Vu, mm/yr"  # change the 3 in -Bx3 for tick label interval on the colourbar
	awk -F "," '(NR>1){print $3, $4, $5}' $points | gmt plot -Sc0.15 -C -Wblack
gmt end show 