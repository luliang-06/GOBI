#!/usr/bin/env bash
gmt set MAP_FRAME_TYPE plain 
gmt set PS_MEDIA a4
gmt set FONT_ANNOT_PRIMARY 12p
gmt set FONT_LABEL 20p
gmt set FORMAT_GEO_MAP D
gmt set FONT_TITLE 14p
gmt set MAP_TICK_LENGTH_PRIMARY 2p 
gmt set MAP_ANNOT_OFFSET_PRIMARY auto
gmt set MAP_LABEL_OFFSET auto
gmt set MAP_TITLE_OFFSET 2p
gmt set MAP_ANNOT_OFFSET_SECONDARY auto

BASE_DIR=$(cd "$(dirname "$0")/../.." && pwd)
points="${BASE_DIR}/data/GWLcr_VU_ModelResult.csv"

vu_all="${BASE_DIR}/data/vu_AHB.nc"
vu_ref="${BASE_DIR}/outputs/gps_ref/vu_shiyang_referenced.nc"

vu_pred_sy="${BASE_DIR}/data/gwl_cr_SYref.nc"
vu_pred_all="${BASE_DIR}/data/gwl_cr_all.nc"

basin="${BASE_DIR}/data/wuwei_level5_basin.gmt"
gps="${BASE_DIR}/data/GPS_merge.csv"

OUT_DIR="${BASE_DIR}/outputs"


# # plot GPS on vu
# gmt begin ${OUT_DIR}/gps_on_vu png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GNSS Vu & InSAR Vu"
#     gmt makecpt -Cvik -T-5/5
# 	gmt grdimage $vu_all -n+c -Q -t20
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '($9!="NaN"){print $2, $3, $9}' $gps | gmt plot -St0.40 -C -W0.6p,black
# 	gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+e+ml -F+gwhite+p0.1p -Bx5+l"Vu (mm/yr)" --FONT_ANNOT_PRIMARY=18p
# gmt end


# # plot GWL change rate  on vu_all
# gmt begin ${OUT_DIR}/gwlcr_on_vuall png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"Observed GWL change rate & InSAR Prediction"	
#     gmt makecpt -Croma -T-1/1 -I
# 	gmt grdimage $vu_pred_all -n+c -Q
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '{print $3, $4, $13}' $points | gmt plot -Sc0.22 -C -W0.4p,black
# 	gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+e+ml -F+gwhite+p0.1p -Bx1+l"@~D@~GWL/@~D@~t  (m/yr)" --FONT_ANNOT_PRIMARY=18p
# gmt end

# # ------ Amplitude ------
# # plot GWL_amp on Vu_amp Descecding
# gmt begin ${OUT_DIR}/gwl_on_vu_amp_d png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GWL amplitude & InSAR Descending amplitude"
#     gmt makecpt -Coslo -T0/5 -I
# 	gmt grdimage ${BASE_DIR}/frames/033D_05106_131313/TS_GEOCml1GACOS/cum_fd.h5_amp.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/135D_05023_131313/TS_GEOCml1GACOS/cum_fd.h5_amp.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/135D_05222_131313/TS_GEOCml1GACOS/cum_fd.h5_amp.nc -n+c -Q
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '{amp=$9; if(amp<0) amp=-amp; print $3, $4, amp}' $points | gmt plot -Sc0.22 -C -W0.4p,black
# 	gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+e+ml -F+gwhite+p0.1p -Bx5+l"Amplitude (mm)" --FONT_ANNOT_PRIMARY=18p
# gmt end

# # plot GWL_amp on Vu_amp Ascending
# gmt begin ${OUT_DIR}/gwl_on_vu_amp_a png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BwESn+t"GWL amplitude & InSAR Ascending amplitude"
#     gmt makecpt -Coslo -T0/5 -I
# 	gmt grdimage ${BASE_DIR}/frames/128A_05172_131313/TS_GEOCml1GACOS/cum_fd.h5_amp.nc -n+c -Q 
# 	gmt grdimage ${BASE_DIR}/frames/055A_05021_131313/TS_GEOCml1GACOS/cum_fd.h5_amp.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/055A_05221_131313/TS_GEOCml1GACOS/cum_fd.h5_amp.nc -n+c -Q
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '{amp=$9; if(amp<0) amp=-amp; print $3, $4, amp}' $points | gmt plot -Sc0.22 -C -W0.4p,black
# 	gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+e+ml -F+gwhite+p0.1p -Bx5+l"Amplitude (mm)" --FONT_ANNOT_PRIMARY=18p
# gmt end

# # ------ ASTD------
# # plot GWL_astd on Vu_astd Descecding
# gmt begin ${OUT_DIR}/gwl_on_vu_astd_d png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GWL astd & InSAR Descending astd"
#     gmt makecpt -Cnuuk -T0/1 -I
# 	gmt grdimage ${BASE_DIR}/frames/033D_05106_131313/TS_GEOCml1GACOS/cum_fd.h5_astd.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/135D_05023_131313/TS_GEOCml1GACOS/cum_fd.h5_astd.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/135D_05222_131313/TS_GEOCml1GACOS/cum_fd.h5_astd.nc -n+c -Q
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '{print $3, $4, $10}' $points | gmt plot -Sc0.22 -C -W0.4p,black
# 	gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+e+ml -F+gwhite+p0.1p -Bx1+l"Amplitude Std (mm)" --FONT_ANNOT_PRIMARY=18p
# gmt end

# # plot GWL_amp on Vu_amp Ascending
# gmt begin ${OUT_DIR}/gwl_on_vu_astd_a png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BwESn+t"GWL astd & InSAR Ascending astd"
#     gmt makecpt -Cnuuk -T0/1 -I
# 	gmt grdimage ${BASE_DIR}/frames/128A_05172_131313/TS_GEOCml1GACOS/cum_fd.h5_astd.nc -n+c -Q 
# 	gmt grdimage ${BASE_DIR}/frames/055A_05021_131313/TS_GEOCml1GACOS/cum_fd.h5_astd.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/055A_05221_131313/TS_GEOCml1GACOS/cum_fd.h5_astd.nc -n+c -Q
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '{print $3, $4, $10}' $points | gmt plot -Sc0.22 -C -W0.4p,black
# 	gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+e+ml -F+gwhite+p0.1p -Bx1+l"Amplitude Std (mm)" --FONT_ANNOT_PRIMARY=18p
# gmt end

# ------ dt ------
# plot GWL_dt on Vu_dt Descecding
gmt begin ${OUT_DIR}/gwl_on_vu_dt_d png
	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GWL phase & InSAR Descending phase"
    gmt makecpt -CromaO -T0/365
	gmt grdimage ${BASE_DIR}/frames/033D_05106_131313/TS_GEOCml1GACOS/cum_fd.h5_delta_t.nc -n+c -Q 
	gmt grdimage ${BASE_DIR}/frames/135D_05023_131313/TS_GEOCml1GACOS/cum_fd.h5_delta_t.nc -n+c -Q
	gmt grdimage ${BASE_DIR}/frames/135D_05222_131313/TS_GEOCml1GACOS/cum_fd.h5_delta_t.nc -n+c -Q
	gmt plot $basin -W0.8p,black
	awk -F "," '{phi=$11*365.25; print $3, $4, phi}' $points | gmt plot -Sc0.22 -C -W0.4p,black
    gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+ml -F+gwhite+p0.1p -Bx182+l"Phase (days)" --FONT_ANNOT_PRIMARY=18p
gmt end

# plot GWL_dt on Vu_dt Ascending
gmt begin ${OUT_DIR}/gwl_on_vu_dt_a png
	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GWL phase & InSAR Ascending phase"
    gmt makecpt -CromaO -T0/365
	gmt grdimage ${BASE_DIR}/frames/128A_05172_131313/TS_GEOCml1GACOS/cum_fd.h5_delta_t.nc -n+c -Q 
	gmt grdimage ${BASE_DIR}/frames/055A_05021_131313/TS_GEOCml1GACOS/cum_fd.h5_delta_t.nc -n+c -Q
	gmt grdimage ${BASE_DIR}/frames/055A_05221_131313/TS_GEOCml1GACOS/cum_fd.h5_delta_t.nc -n+c -Q
	gmt plot $basin -W0.8p,black
	awk -F "," '{phi=$11*365.25; print $3, $4, phi}' $points | gmt plot -Sc0.22 -C -W0.4p,black
    gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+ml -F+gwhite+p0.1p -Bx182+l"Phase (days)" --FONT_ANNOT_PRIMARY=18p
gmt end

# # ------ vstd ------
# # plot GWL_vstd on Vu_vstd Descecding
# gmt begin ${OUT_DIR}/gwl_on_vu_vstd_d png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GWL vstd & InSAR Descending vstd"
#     gmt makecpt -Cviridis -T0/1 -I
# 	gmt grdimage ${BASE_DIR}/frames/033D_05106_131313/TS_GEOCml1GACOS/cum_filt.h5_vstd.nc -n+c -Q 
# 	gmt grdimage ${BASE_DIR}/frames/135D_05023_131313/TS_GEOCml1GACOS/cum_filt.h5_vstd.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/135D_05222_131313/TS_GEOCml1GACOS/cum_filt.h5_vstd.nc -n+c -Q
#     gmt colorbar -DjTL+w1.8/13%+o1/1+h+e+ml -F+gwhite+p0.1p -Bx1+l"Vstd" -By+l"mm/yr"
# 	awk -F "," '(NR>1){print $3, $4, $14*1000}' $points | gmt plot -Sc0.22 -C -W0.4p,black
# gmt end

# # plot GWL_vstd on Vu_vstd Ascending
# gmt begin ${OUT_DIR}/gwl_on_vu_vstd_a png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GWL vstd & InSAR Ascending vstd"
#     gmt makecpt -Cviridis -T0/1 -I
# 	gmt grdimage ${BASE_DIR}/frames/128A_05172_131313/TS_GEOCml1GACOS/cum_filt.h5_vstd.nc -n+c -Q 
# 	gmt grdimage ${BASE_DIR}/frames/055A_05021_131313/TS_GEOCml1GACOS/cum_filt.h5_vstd.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/055A_05221_131313/TS_GEOCml1GACOS/cum_filt.h5_vstd.nc -n+c -Q
#     gmt colorbar -DjTL+w1.8/13%+o1/1+h+e+ml -F+gwhite+p0.1p -Bx1+l"Vstd" -By+l"mm/yr"
# 	awk -F "," '(NR>1){print $3, $4, $14*1000}' $points | gmt plot -Sc0.22 -C -W0.4p,black
# gmt end