#!/usr/bin/env bash
gmt set MAP_FRAME_TYPE plain 
gmt set PS_MEDIA a4
gmt set FONT_ANNOT_PRIMARY 12
gmt set FONT_LABEL 12
gmt set FORMAT_GEO_MAP D
gmt set FONT_TITLE 16p
gmt set MAP_TICK_LENGTH_PRIMARY 2p 
gmt set MAP_ANNOT_OFFSET_PRIMARY auto
gmt set MAP_LABEL_OFFSET auto
gmt set MAP_TITLE_OFFSET 2p
gmt set MAP_ANNOT_OFFSET_SECONDARY auto

BASE_DIR=$(cd "$(dirname "$0")/../.." && pwd)
points="${BASE_DIR}/outputs_test/GWLcr_VU_ModelResult.csv"
vu_shiyang="${BASE_DIR}/outputs_test/gwl_cr_SYref.nc"
vu_shiyang_all="${BASE_DIR}/outputs_test/gwl_cr_SYref_all.nc"
OUT_DIR="${BASE_DIR}/outputs_test"

# points=/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/data/GWLcr_VU_ModelResult.csv # or a separate txt file (if comma delimited, you'll need to change the awk statement below slightly)
# gps=/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/data/GPS_merge.csv

# raster=/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/data/gwl_cr_all.nc
# vu_shiyang=/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/outputs/gwl_cr_SYref.nc
# vu_AHB=/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/data/vu_AHB.nc
# vu_ref=/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/outputs/gps_ref/vu_shiyang_referenced.nc

# out_dir=/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/outputs/


# # plot GPS on vu
# gmt begin ${out_dir}/gps_on_vu png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GNSS Vu & InSAR Vu"							# -R: map extent ｜ -J: projection | -B: axis interval | -B: map frame (capital: label & ticks)
#     gmt makecpt -Croma -T-5/5 -I 													# change the limits of your colour map
# 	gmt grdimage $vu_ref -n+c -Q -t15											    # -n: interpolation | +c: clip | -Q: set nans as transparent
#     gmt colorbar -DjTL+w1.8/13%+o1/1+h+e+ml -F+gwhite+p0.1p -Bx5+l"Vu" -By+l"mm/yr" 						# change the 3 in -Bx3 for tick label interval on the colourbar
# 	awk -F "," '(NR>1 && $9!=1000){print $2, $3, $9}' $gps | gmt plot -St0.35 -C -W0.6p,black
# gmt end


# plot GWL change rate  on vu
gmt begin ${out_dir}/gwlcr_on_vu png
	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"Observed GWL change rate & InSAR Prediction"							# -R: map extent ｜ -J: projection | -B: axis interval | -B: map frame (capital: label & ticks)
    gmt makecpt -Croma -T-1/1 -I 													# change the limits of your colour map
	gmt grdimage $vu_shiyang -n+c -Q 												    # -n: interpolation | +c: clip | -Q: set nans as transparent
    gmt colorbar -DjTL+w1.8/13%+o1/1+h+e+ml -F+gwhite+p0.1p -Bx1+l"@~D@~GWL/@~D@~t" -By+l"m/yr"						# change the 3 in -Bx3 for tick label interval on the colourbar
	awk -F "," '(NR>1){print $3, $4, $13}' $points | gmt plot -Sc0.22 -C -W0.4p,black
gmt end


# plot GWL change rate  on vu_all
gmt begin ${out_dir}/gwlcr_on_vuall png
	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"Observed GWL change rate & InSAR Prediction"							# -R: map extent ｜ -J: projection | -B: axis interval | -B: map frame (capital: label & ticks)
    gmt makecpt -Croma -T-1/1 -I 													# change the limits of your colour map
	gmt grdimage $vu_shiyang_all -n+c -Q 												    # -n: interpolation | +c: clip | -Q: set nans as transparent
    gmt colorbar -DjTL+w1.8/13%+o1/1+h+e+ml -F+gwhite+p0.1p -Bx1+l"@~D@~GWL/@~D@~t" -By+l"m/yr"						# change the 3 in -Bx3 for tick label interval on the colourbar
	awk -F "," '(NR>1){print $3, $4, $13}' $points | gmt plot -Sc0.22 -C -W0.4p,black
gmt end


# # plot points on raster
# gmt begin points_on_raster png,pdf
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn  # draw the map frame, change the boundary to -Rleft/right/bottom/top -B5 for a grid tick every 5 degrees, play with how you capitalise wesn after the second -B
#     gmt makecpt -Croma -T-1/1 -I # change the limits of your colour map
# 	gmt grdimage $raster -n+c -Q 
#     gmt colorbar -DjTL+w1.8/13%+o1/1+h+e+ml -Bx1+l"Vu, mm/yr"  # change the 3 in -Bx3 for tick label interval on the colourbar
# 	awk -F "," '(NR>1){print $3, $4, $5}' $points | gmt plot -Sc0.15 -C -Wblack
# gmt end