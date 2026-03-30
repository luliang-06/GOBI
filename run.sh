#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "Running plot_ts_new.py"
python scripts/plot_ts_new.py

echo "Converting tif to NetCDF"
gdal_translate -of netCDF ../outputs/pred_GWLcr_VU.tif ../outputs/pred_GWLcr_VU.nc
gdal_translate -of netCDF ../outputs/pred_GWLcr_VUall.tif ../outputs/pred_GWLcr_VUall.nc

echo "GMT plot"
./scripts/gmt_plot_points_on_raster.sh

echo "Dropping lon/lat columns from CSV"
python3 -c "import pandas as pd; df = pd.read_csv('../outputs/GWLcr_VU_ModelResult.csv'); df.drop(columns=['lon', 'lat']).to_csv('../outputs/GWLcr_VU_ModelResult.csv', index=False)"

echo "Check: CSV head"
python3 -c "import pandas as pd; print(pd.read_csv('../outputs/GWLcr_VU_ModelResult.csv').head(5))"

echo "Finished."
