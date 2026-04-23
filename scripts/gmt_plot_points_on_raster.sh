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

landcover="${BASE_DIR}/data/shiyang_landcover.nc"
permafrost="${BASE_DIR}/data/shiyang_permafrost.nc"
river="${BASE_DIR}/data/shiyang_rivers.gmt"
basin="${BASE_DIR}/data/shiyang_outline.gmt"
glacier="${BASE_DIR}/data/shiyang_glacier.gmt"
gps="${BASE_DIR}/data/GPS_merge.csv"

OUT_DIR="${BASE_DIR}/outputs"


# # plot study area DEM
# gmt begin ${OUT_DIR}/shiyang_elevation png
# 	gmt basemap -R101.2/104.0/37.0/39.5 -JX6i -B1
# 	gmt grdimage @earth_relief_03s -I+d -CgrayC -t30
# 	gmt clip $basin
# 	gmt makecpt -Cdem2 -T1000/4500
# 	gmt grdimage @earth_relief_03s -I+d -C -t0
# 	gmt clip -C
# 	gmt plot $basin -W0.8p,black
# 	gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+ml -F+gwhite+p0.1p -Bx1000+l"Elevation (m)" --FONT_ANNOT_PRIMARY=18p
# gmt end

# gmt begin ${OUT_DIR}/location_map png
#     gmt basemap -R73/135/20/55 -JM6i -B10
#     gmt grdimage @earth_relief_02m -I+d -Cgray
#     gmt coast -W0.3p,black -N1/0.5p,gray50
#     gmt plot $basin -W1.5p,red -Gred@60
# gmt end

# plot wells on landcover
gmt begin ${OUT_DIR}/shiyang_landcover png
	gmt basemap -R101.2/104.0/37.0/39.5 -JX6i -B1 -BwESn
	gmt grdimage @earth_relief_03s -I+d -Cgray -t30
	gmt clip $basin
	gmt grdimage $landcover -Clandcover.cpt -T0/1 -Q -nn
	gmt plot $glacier -W0.8p,
	gmt clip -C
	gmt makecpt -Cacton -I
	gmt grdimage $permafrost -C -n+c -Q -t15
	gmt plot $river -W0.8p,#0a33ff
	gmt plot $glacier -W0.8p,#00f7ff
	gmt plot $basin -W0.8p,black
	awk -F "," '{print $3, $4}' $points | gmt plot -Sc0.2 -G138/208/255 -W0.4p,black
	cat << 'EOF' | gmt legend -DjTL+w4.5c+o0.2c/0.2c -F+p0.5p+g255/255/255@30
G 0.1c
S 0.3c s 0.3c  68/101/137  0.3p  0.6c  Water
S 0.3c s 0.3c  38/115/0    0.3p  0.6c  Trees
S 0.3c s 0.3c  255/211/76  0.3p  0.6c  Cropland
S 0.3c s 0.3c  220/60/60   0.3p  0.6c  Urban
S 0.3c s 0.3c  194/161/108 0.3p  0.6c  Bare ground
S 0.3c s 0.3c  204/230/153 0.3p  0.6c  Rangeland
S 0.3c s 0.3c  136/77/232  0.3p  0.6c  Permafrost
S 0.3c c 0.2c  138/208/255 0.4p,black 0.6c Monitoring wells
S 0.3c - 0.5c - 1.5p,#0a33ff 0.6c River
S 0.3c - 0.5c - 1.5p,#00f7ff 0.6c Glacier
EOF
gmt end


# # plot GPS on vu
# gmt begin ${OUT_DIR}/gps_on_vu png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GNSS Vu & InSAR Vu"
#     gmt makecpt -Cvik -T-5/5
# 	gmt grdimage $vu_all -n+c -Q -t20
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '(NR>1)($9!="NaN"){print $2, $3, $9}' $gps | gmt plot -St0.40 -C -W0.6p,black
# 	gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+e+ml -F+gwhite+p0.1p -Bx5+l"Vu (mm/yr)" --FONT_ANNOT_PRIMARY=18p
# gmt end


# # plot GWL change rate  on vu_all
# gmt begin ${OUT_DIR}/gwlcr_on_vuall png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"Observed GWL change rate & InSAR Prediction"	
#     gmt makecpt -Croma -T-1/1 -I
# 	gmt grdimage $vu_pred_all -n+c -Q
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '(NR>1){print $3, $4, $13}' $points | gmt plot -Sc0.22 -C -W0.4p,black
# 	gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+e+ml -F+gwhite+p0.1p -Bx1+l"@~D@~GWL/@~D@~t  (m/yr)" --FONT_ANNOT_PRIMARY=18p
# gmt end

# # ------ Amplitude ------
# gmt makecpt -Coslo -T0/8 -I > vu_amp.cpt
# gmt makecpt -Coslo -T0/50 -I > gw_amp.cpt
# # plot GWL_amp on Vu_amp Ascending
# gmt begin ${OUT_DIR}/gwl_on_vu_amp_a png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GWL amplitude & InSAR Ascending amplitude"
# 	gmt grdimage ${BASE_DIR}/frames/128A_05172_131313/TS_GEOCml1GACOS/cum_fd.h5_amp.nc -n+c -Q -Cvu_amp.cpt
# 	gmt grdimage ${BASE_DIR}/frames/055A_05021_131313/TS_GEOCml1GACOS/cum_fd.h5_amp.nc -n+c -Q -Cvu_amp.cpt
# 	gmt grdimage ${BASE_DIR}/frames/055A_05221_131313/TS_GEOCml1GACOS/cum_fd.h5_amp.nc -n+c -Q -Cvu_amp.cpt
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '(NR>1){amp=$9/0.0469; if(amp<0) amp=-amp; print $3, $4, amp}' $points | gmt plot -Sc0.22 -Cgw_amp.cpt -W0.5p,white
# 	gmt colorbar -Cvu_amp.cpt -DjTL+w1.25i/0.12i+o1/1+h+e+ml -F+gwhite+p0.1p -Bx8+l"Vu Amplitude (mm)" --FONT_ANNOT_PRIMARY=18p
# 	gmt colorbar -Cgw_amp.cpt -DjTR+w1.25i/0.12i+o1/1+h+e+ml -F+gwhite+p0.1p -Bx25+l"GWL Amplitude (mm)" --FONT_ANNOT_PRIMARY=18p
# gmt end

# # plot GWL_amp on Vu_amp Descecding
# gmt begin ${OUT_DIR}/gwl_on_vu_amp_d png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BwESn+t"GWL amplitude & InSAR Descending amplitude"
# 	gmt grdimage ${BASE_DIR}/frames/033D_05106_131313/TS_GEOCml1GACOS/cum_fd.h5_amp.nc -n+c -Q -Cvu_amp.cpt
# 	gmt grdimage ${BASE_DIR}/frames/135D_05023_131313/TS_GEOCml1GACOS/cum_fd.h5_amp.nc -n+c -Q -Cvu_amp.cpt
# 	gmt grdimage ${BASE_DIR}/frames/135D_05222_131313/TS_GEOCml1GACOS/cum_fd.h5_amp.nc -n+c -Q -Cvu_amp.cpt
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '(NR>1){amp=$9/0.0469; if(amp<0) amp=-amp; print $3, $4, amp}' $points | gmt plot -Sc0.22 -Cgw_amp.cpt -W0.5p,white
# 	gmt colorbar -Cvu_amp.cpt -DjTL+w1.25i/0.12i+o1/1+h+e+ml -F+gwhite+p0.1p -Bx8+l"Vu Amplitude (mm)" --FONT_ANNOT_PRIMARY=18p
# 	gmt colorbar -Cgw_amp.cpt -DjTR+w1.25i/0.12i+o1/1+h+e+ml -F+gwhite+p0.1p -Bx25+l"GWL Amplitude (mm)" --FONT_ANNOT_PRIMARY=18p
# gmt end

# # ------ ASTD ------
# # plot GWL_amp on Vu_amp Ascending
# gmt begin ${OUT_DIR}/gwl_on_vu_astd_a png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GWL astd & InSAR Ascending astd"
#     gmt makecpt -Cnuuk -T0/2 -I
# 	gmt grdimage ${BASE_DIR}/frames/128A_05172_131313/TS_GEOCml1GACOS/cum_fd.h5_astd.nc -n+c -Q 
# 	gmt grdimage ${BASE_DIR}/frames/055A_05021_131313/TS_GEOCml1GACOS/cum_fd.h5_astd.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/055A_05221_131313/TS_GEOCml1GACOS/cum_fd.h5_astd.nc -n+c -Q
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '(NR>1){astd=$10/0.0469; print $3, $4, astd}' $points | gmt plot -Sc0.22 -C -W0.4p,black
# 	gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+e+ml -F+gwhite+p0.1p -Bx1+l"Amplitude Std (mm)" --FONT_ANNOT_PRIMARY=18p
# gmt end

# # plot GWL_astd on Vu_astd Descecding
# gmt begin ${OUT_DIR}/gwl_on_vu_astd_d png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BwESn+t"GWL astd & InSAR Descending astd"
#     gmt makecpt -Cnuuk -T0/2 -I
# 	gmt grdimage ${BASE_DIR}/frames/033D_05106_131313/TS_GEOCml1GACOS/cum_fd.h5_astd.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/135D_05023_131313/TS_GEOCml1GACOS/cum_fd.h5_astd.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/135D_05222_131313/TS_GEOCml1GACOS/cum_fd.h5_astd.nc -n+c -Q
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '(NR>1){astd=$10/0.0469; print $3, $4, astd}' $points | gmt plot -Sc0.22 -C -W0.4p,black
# 	gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+e+ml -F+gwhite+p0.1p -Bx1+l"Amplitude Std (mm)" --FONT_ANNOT_PRIMARY=18p
# gmt end

# # ------ dt ------
# # plot GWL_dt on Vu_dt Ascending
# gmt begin ${OUT_DIR}/gwl_on_vu_dt_a png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GWL phase & InSAR Ascending phase"
#     gmt makecpt -CromaO -T0/365.25
# 	gmt grdimage ${BASE_DIR}/frames/055A_05221_131313/TS_GEOCml1GACOS/cum_fd.h5_delta_t.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/055A_05021_131313/TS_GEOCml1GACOS/cum_fd.h5_delta_t.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/128A_05172_131313/TS_GEOCml1GACOS/cum_fd.h5_delta_t.nc -n+c -Q 
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '(NR>1){print $3, $4, $11}' $points | gmt plot -Sc0.22 -C -W0.4p,black
#     gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+ml -F+gwhite+p0.1p -Bx365.25+l"Phase (days)" --FONT_ANNOT_PRIMARY=18p
# gmt end

# # plot GWL_dt on Vu_dt Descecding
# gmt begin ${OUT_DIR}/gwl_on_vu_dt_d png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BwESn+t"GWL phase & InSAR Descending phase"
#     gmt makecpt -CromaO -T0/365.25
# 	gmt grdimage ${BASE_DIR}/frames/135D_05023_131313/TS_GEOCml1GACOS/cum_fd.h5_delta_t.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/033D_05106_131313/TS_GEOCml1GACOS/cum_fd.h5_delta_t.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/135D_05222_131313/TS_GEOCml1GACOS/cum_fd.h5_delta_t.nc -n+c -Q
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '(NR>1){print $3, $4, $11}' $points | gmt plot -Sc0.22 -C -W0.4p,black
#     gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+ml -F+gwhite+p0.1p -Bx365.25+l"Phase (days)" --FONT_ANNOT_PRIMARY=18p
# gmt end

# # ------ diff of dt ------
# gmt makecpt -Croma -T-10/10 -I > vu.cpt
# gmt makecpt -Cturku -T0/180 -I -H > timelag.cpt
# # plot dt diff on Vu Ascending
# gmt begin ${OUT_DIR}/time_lag_on_vu_a png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"Time Lag & Vel Ascending"
# 	gmt grdimage ${BASE_DIR}/frames/128A_05172_131313/TS_GEOCml1GACOS/cum_fd.h5_vel.nc -n+c -Q -Cvu.cpt
# 	gmt grdimage ${BASE_DIR}/frames/055A_05021_131313/TS_GEOCml1GACOS/cum_fd.h5_vel.nc -n+c -Q -Cvu.cpt
# 	gmt grdimage ${BASE_DIR}/frames/055A_05221_131313/TS_GEOCml1GACOS/cum_fd.h5_vel.nc -n+c -Q -Cvu.cpt
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '(NR>1){lag=$21; if(lag<0) lag=-lag; print $3, $4, lag}' $points | gmt plot -Sc0.22 -Ctimelag.cpt -W0.4p,black
#     gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+e+ml -Cvu.cpt -F+gwhite+p0.1p -Bx10+l"Velocity (m/yr)" --FONT_ANNOT_PRIMARY=18p
# 	gmt colorbar -DjTR+w1.25i/0.12i+o1/1+h+e+ml -Ctimelag.cpt -F+gwhite+p0.1p -Bx180+l"Time lag (days)" --FONT_ANNOT_PRIMARY=18p
# gmt end

# # plot dt diff on Vu Descecding
# gmt begin ${OUT_DIR}/time_lag_on_vu_d png
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BwESn+t"Time Lag & Vel Descending"
# 	gmt grdimage ${BASE_DIR}/frames/033D_05106_131313/TS_GEOCml1GACOS/cum_fd.h5_vel.nc -n+c -Q -Cvu.cpt
# 	gmt grdimage ${BASE_DIR}/frames/135D_05023_131313/TS_GEOCml1GACOS/cum_fd.h5_vel.nc -n+c -Q -Cvu.cpt
# 	gmt grdimage ${BASE_DIR}/frames/135D_05222_131313/TS_GEOCml1GACOS/cum_fd.h5_vel.nc -n+c -Q -Cvu.cpt
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '(NR>1){lag=$21; if(lag<0) lag=-lag; print $3, $4, lag}' $points | gmt plot -Sc0.22 -Ctimelag.cpt -W0.4p,black
#     gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+e+ml -Cvu.cpt -F+gwhite+p0.1p -Bx10+l"Velocity (m/yr)" --FONT_ANNOT_PRIMARY=18p
# 	gmt colorbar -DjTR+w1.25i/0.12i+o1/1+h+e+ml -Ctimelag.cpt -F+gwhite+p0.1p -Bx180+l"Time lag (days)" --FONT_ANNOT_PRIMARY=18p
# gmt end

# # ------ VU ------
# # plot GWL_cr on Vu Ascending
# gmt begin ${OUT_DIR}/gwl_on_vu_a png
# 	# gmt basemap -R99.9/105.5/36.5/41.1 -JX6i -B1 -BWeSn+t"Filted Deramped Velocity (Ascending Track)"
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"Groundwater Change Rate on Velocity (Ascending Track)"
# 	# gmt grdimage @earth_relief_03s -I+d -Cgray
# 	gmt makecpt -Croma -T-10/10 -I
# 	gmt grdimage ${BASE_DIR}/frames/128A_05172_131313/TS_GEOCml1GACOS/cum_fd.h5_vel.nc -n+c -Q 
# 	gmt grdimage ${BASE_DIR}/frames/055A_05021_131313/TS_GEOCml1GACOS/cum_fd.h5_vel.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/055A_05221_131313/TS_GEOCml1GACOS/cum_fd.h5_vel.nc -n+c -Q
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '(NR>1){print $3, $4, $13/0.0469}' $points | gmt plot -Sc0.22 -C -W0.4p,black
# 	gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+e+ml -F+gwhite+p0.1p -Bx10+l"Velocity (mm/yr)" --FONT_ANNOT_PRIMARY=18p
# gmt end

# # plot GWL_cr on Vu Descecding
# gmt begin ${OUT_DIR}/gwl_on_vu_d png
# 	# gmt basemap -R99.9/105.5/36.5/41.1 -JX6i -B1 -BwESn+t"Filted Deramped Velocity (Descending Track)"
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BwESn+t"Groundwater Change Rate on Velocity  (Descending Track)"
# 	# gmt grdimage @earth_relief_03s -I+d -Cgray
# 	gmt makecpt -Croma -T-10/10 -I
# 	gmt grdimage ${BASE_DIR}/frames/033D_05106_131313/TS_GEOCml1GACOS/cum_fd.h5_vel.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/135D_05023_131313/TS_GEOCml1GACOS/cum_fd.h5_vel.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/135D_05222_131313/TS_GEOCml1GACOS/cum_fd.h5_vel.nc -n+c -Q
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '(NR>1){print $3, $4, $13/0.0469}' $points | gmt plot -Sc0.22 -C -W0.4p,black
# 	gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+e+ml -F+gwhite+p0.1p -Bx10+l"velocity (mm/yr)" --FONT_ANNOT_PRIMARY=18p
# gmt end

# # ------ vstd ------
# # plot GWL_vstd on Vu_vstd Ascending
# gmt begin ${OUT_DIR}/gwl_on_vu_vstd_a png
# 	# gmt basemap -R99.9/105.5/36.5/41.1 -JX6i -B1 -BWeSn+t"Filted Deramped Velocity Std (Ascending Track)"
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BWeSn+t"GWL Change Rate Std on Velocity Std (Ascending Track)"
# 	# gmt grdimage @earth_relief_03s -I+d -Cgray
# 	gmt makecpt -CbatlowW -T0/1 -I
# 	gmt grdimage ${BASE_DIR}/frames/128A_05172_131313/TS_GEOCml1GACOS/cum_fd.h5_vstd.nc -n+c -Q 
# 	gmt grdimage ${BASE_DIR}/frames/055A_05021_131313/TS_GEOCml1GACOS/cum_fd.h5_vstd.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/055A_05221_131313/TS_GEOCml1GACOS/cum_fd.h5_vstd.nc -n+c -Q
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '(NR>1){print $3, $4, $14/0.0469}' $points | gmt plot -Sc0.22 -C -W0.4p,black
#     gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+e+ml -F+gwhite+p0.1p -Bx1+l"Vstd (mm/yr)" --FONT_ANNOT_PRIMARY=18p
# gmt end

# # plot GWL_vstd on Vu_vstd Descecding
# gmt begin ${OUT_DIR}/gwl_on_vu_vstd_d png
# 	# gmt basemap -R99.9/105.5/36.5/41.1 -JX6i -B1 -BwESn+t"Filted Deramped Velocity Std (Descending Track)"
# 	gmt basemap -R101.7/104.7/37.3/39.3 -JX6i -B1 -BwESn+t"GWL Change Rate Std on Velocity Std  (Descending Track)"
# 	# gmt grdimage @earth_relief_03s -I+d -Cgray
# 	gmt makecpt -CbatlowW -T0/1 -I
# 	gmt grdimage ${BASE_DIR}/frames/033D_05106_131313/TS_GEOCml1GACOS/cum_fd.h5_vstd.nc -n+c -Q 
# 	gmt grdimage ${BASE_DIR}/frames/135D_05023_131313/TS_GEOCml1GACOS/cum_fd.h5_vstd.nc -n+c -Q
# 	gmt grdimage ${BASE_DIR}/frames/135D_05222_131313/TS_GEOCml1GACOS/cum_fd.h5_vstd.nc -n+c -Q
# 	gmt plot $basin -W0.8p,black
# 	awk -F "," '(NR>1){print $3, $4, $14/0.0469}' $points | gmt plot -Sc0.22 -C -W0.4p,black
#     gmt colorbar -DjTL+w1.25i/0.12i+o1/1+h+e+ml -F+gwhite+p0.1p -Bx1+l"Vstd (mm/yr)" --FONT_ANNOT_PRIMARY=18p
# gmt end