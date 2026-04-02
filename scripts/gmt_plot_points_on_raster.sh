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
points="${BASE_DIR}/data/GWLcr_VU_ModelResult.csv"
vu="${BASE_DIR}/data/gwl_cr_SYref.nc"
vu_all="${BASE_DIR}/outputs/pred_GWLcr_VUall.nc"

OUT_DIR="${BASE_DIR}/outputs"

# points=/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/data/GWLcr_VU_ModelResult.csv # or a separate txt file (if comma delimited, you'll need to change the awk statement below slightly)
# gps=/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/data/GPS_merge.csv

# raster=/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/data/gwl_cr_all.nc
# vu_shiyang=/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/outputs/gwl_cr_SYref.nc
# vu_AHB=/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/data/vu_AHB.nc
# vu_ref=/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/outputs/gps_ref/vu_shiyang_referenced.nc

# out_dir=/exports/geos.ed.ac.uk/comet/lliang/GOBI_proj/outputs/


# # plot GPS on vu
# gmt begin ${out_dir}/gps_on_vu png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GNSS Vu & InSAR Vu"
#     gmt makecpt -Croma -T-5/5 -I
# 	gmt grdimage $vu_ref -n+c -Q -t15
#     gmt colorbar -DjTL+w1.8/13%+o1/1+h+e+ml -F+gwhite+p0.1p -Bx5+l"Vu" -By+l"mm/yr"
# 	awk -F "," '(NR>1 && $9!=1000){print $2, $3, $9}' $gps | gmt plot -St0.35 -C -W0.6p,black
# gmt end


# # plot GWL change rate  on vu
# gmt begin ${OUT_DIR}/gwl_on_vu_change_rate png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"Observed GWL change rate & InSAR Prediction"		# -R: map extent ｜ -J: projection | -B: axis interval | -B: map frame (capital: label & ticks)
#     gmt makecpt -Croma -T-1/1 -I 																			# change the limits of your colour map
# 	gmt grdimage $vu -n+c -Q 												    							# -n: interpolation | +c: clip | -Q: set nans as transparent
#     gmt colorbar -DjTL+w1.8/13%+o1/1+h+e+ml -F+gwhite+p0.1p -Bx1+l"@~D@~GWL/@~D@~t" -By+l"m/yr"			# change the 3 in -Bx3 for tick label interval on the colourbar
# 	awk -F "," '(NR>1){print $3, $4, $13}' $points | gmt plot -Sc0.22 -C -W0.4p,black
# gmt end


# # plot GWL change rate  on vu_all
# gmt begin ${OUT_DIR}/gwlcr_on_vuall png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"Observed GWL change rate & InSAR Prediction"	
#     gmt makecpt -Croma -T-1/1 -I
# 	gmt grdimage $vu_all -n+c -Q
#     gmt colorbar -DjTL+w1.8/13%+o1/1+h+e+ml -F+gwhite+p0.1p -Bx1+l"@~D@~GWL/@~D@~t" -By+l"m/yr"
# 	awk -F "," '(NR>1){print $3, $4, $13}' $points | gmt plot -Sc0.22 -C -W0.4p,black
# gmt end

# # Amplitude
# # plot GWL_amp on Vu_amp Descecding
# gmt begin ${OUT_DIR}/gwl_on_vu_amp_d png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GWL amplitude & InSAR Descending amplitude"
#     gmt makecpt -Croma -T0/20 -I
# 	gmt grdimage ${BASE_DIR}/frames/033D_05106_131313/TS_GEOCml1GACOS/cum_filt.h5_amp.nc -n+c -Q 
# 	gmt grdimage ${BASE_DIR}/frames/135D_05023_131313/TS_GEOCml1GACOS/cum_filt.h5_amp.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/135D_05222_131313/TS_GEOCml1GACOS/cum_filt.h5_amp.nc -n+c -Q
#     gmt colorbar -DjTL+w1.8/13%+o1/1+h+e+ml -F+gwhite+p0.1p -Bx10+l"@~D@~GWL/@~D@~t" -By+l"mm"
# 	awk -F "," '(NR>1){print $3, $4, $9*1000}' $points | gmt plot -Sc0.22 -C -W0.4p,black
# gmt end

# # plot GWL_amp on Vu_amp Ascending
# gmt begin ${OUT_DIR}/gwl_on_vu_amp_a png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GWL amplitude & InSAR Ascending amplitude"
#     gmt makecpt -Croma -T0/20 -I
# 	gmt grdimage ${BASE_DIR}/frames/128A_05172_131313/TS_GEOCml1GACOS/cum_filt.h5_amp.nc -n+c -Q 
# 	gmt grdimage ${BASE_DIR}/frames/055A_05021_131313/TS_GEOCml1GACOS/cum_filt.h5_amp.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/055A_05221_131313/TS_GEOCml1GACOS/cum_filt.h5_amp.nc -n+c -Q
#     gmt colorbar -DjTL+w1.8/13%+o1/1+h+e+ml -F+gwhite+p0.1p -Bx10+l"@~D@~GWL/@~D@~t" -By+l"mm"
# 	awk -F "," '(NR>1){print $3, $4, $9*1000}' $points | gmt plot -Sc0.22 -C -W0.4p,black
# gmt end

# dt
# plot GWL_dt on Vu_dt Descecding
gmt begin ${OUT_DIR}/gwl_on_vu_dt_d png
	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GWL phase & InSAR Descending phase"
    gmt makecpt -CromaO -T-182/182 -I
	gmt grdimage ${BASE_DIR}/frames/033D_05106_131313/TS_GEOCml1GACOS/cum_filt.h5_delta_t.nc -n+c -Q 
	gmt grdimage ${BASE_DIR}/frames/135D_05023_131313/TS_GEOCml1GACOS/cum_filt.h5_delta_t.nc -n+c -Q
	gmt grdimage ${BASE_DIR}/frames/135D_05222_131313/TS_GEOCml1GACOS/cum_filt.h5_delta_t.nc -n+c -Q
	gmt grdinfo ${BASE_DIR}/frames/033D_05106_131313/TS_GEOCml1GACOS/cum_filt.h5_delta_t.nc
	gmt grdinfo ${BASE_DIR}/frames/135D_05023_131313/TS_GEOCml1GACOS/cum_filt.h5_delta_t.nc | grep "v_min"
	gmt grdinfo ${BASE_DIR}/frames/135D_05222_131313/TS_GEOCml1GACOS/cum_filt.h5_delta_t.nc | grep "v_min"
    gmt colorbar -DjTL+w1.8/13%+o1/1+h+ml -F+gwhite+p0.1p -Bx182+l"@~D@~GWL/@~D@~t" -By+l"days"
	awk -F "," '(NR>1){print $3, $4, $11*365.25/(2*3.14159265)}' $points | gmt plot -Sc0.22 -C -W0.4p,black
gmt end

# plot GWL_dt on Vu_dt Ascending
gmt begin ${OUT_DIR}/gwl_on_vu_dt_a png
	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GWL phase & InSAR Ascending phase"
    gmt makecpt -CromaO -T-182/182 -I
	gmt grdimage ${BASE_DIR}/frames/128A_05172_131313/TS_GEOCml1GACOS/cum_filt.h5_delta_t.nc -n+c -Q 
	gmt grdimage ${BASE_DIR}/frames/055A_05021_131313/TS_GEOCml1GACOS/cum_filt.h5_delta_t.nc -n+c -Q
	gmt grdimage ${BASE_DIR}/frames/055A_05221_131313/TS_GEOCml1GACOS/cum_filt.h5_delta_t.nc -n+c -Q
    gmt colorbar -DjTL+w1.8/13%+o1/1+h+ml -F+gwhite+p0.1p -Bx182+l"@~D@~GWL/@~D@~t" -By+l"days"
	awk -F "," '(NR>1){print $3, $4, $11*365.25/(2*3.14159265)}' $points | gmt plot -Sc0.22 -C -W0.4p,black
gmt end

# vstd
# plot GWL_vstd on Vu_vstd Descecding
gmt begin ${OUT_DIR}/gwl_on_vu_vstd_d png
	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GWL vstd & InSAR Descending vstd"
    gmt makecpt -Cviridis -T0/1 -I
	gmt grdimage ${BASE_DIR}/frames/033D_05106_131313/TS_GEOCml1GACOS/cum_filt.h5_vstd.nc -n+c -Q 
	gmt grdimage ${BASE_DIR}/frames/135D_05023_131313/TS_GEOCml1GACOS/cum_filt.h5_vstd.nc -n+c -Q
	gmt grdimage ${BASE_DIR}/frames/135D_05222_131313/TS_GEOCml1GACOS/cum_filt.h5_vstd.nc -n+c -Q
    gmt colorbar -DjTL+w1.8/13%+o1/1+h+e+ml -F+gwhite+p0.1p -Bx1+l"Vstd" -By+l"mm/yr"
	awk -F "," '(NR>1){print $3, $4, $14*1000}' $points | gmt plot -Sc0.22 -C -W0.4p,black
gmt end

# plot GWL_vstd on Vu_vstd Ascending
gmt begin ${OUT_DIR}/gwl_on_vu_vstd_a png
	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GWL vstd & InSAR Ascending vstd"
    gmt makecpt -Cviridis -T0/1 -I
	gmt grdimage ${BASE_DIR}/frames/128A_05172_131313/TS_GEOCml1GACOS/cum_filt.h5_vstd.nc -n+c -Q 
	gmt grdimage ${BASE_DIR}/frames/055A_05021_131313/TS_GEOCml1GACOS/cum_filt.h5_vstd.nc -n+c -Q
	gmt grdimage ${BASE_DIR}/frames/055A_05221_131313/TS_GEOCml1GACOS/cum_filt.h5_vstd.nc -n+c -Q
    gmt colorbar -DjTL+w1.8/13%+o1/1+h+e+ml -F+gwhite+p0.1p -Bx1+l"Vstd" -By+l"mm/yr"
	awk -F "," '(NR>1){print $3, $4, $14*1000}' $points | gmt plot -Sc0.22 -C -W0.4p,black
gmt end