# GOBI — Groundwater Observation from InSAR

This project estimates groundwater level (GWL) change rates across the Shiyang Basin using InSAR-derived vertical displacement (VU) data, and validates the results against observed well measurements.

---

## Overview

The workflow has four main steps:

**Step 1 — Time series analysis and sinusoidal model fitting**

For each groundwater well, the observed GWL time series and the co-located InSAR cumulative displacement (cumU) are plotted together. A sinusoidal model is fitted to extract the linear trend (change rate) and seasonal component from both signals.

<!-- Insert figure: scatter plot of GWL vs InSAR cumU with model fit -->
![GWL vs InSAR time series](figures/F033D_05106_131313_W620302210018.png)

**Step 2 — Regression: GWL change rate vs VU**

The GWL change rates from all wells are compared against InSAR VU values extracted at the same locations. A weighted least-squares (WLS) regression is fitted to derive the relationship:

```
GWL change rate = a × VU + b   (m/yr)
```

**Step 3 — Predict GWL change rate from InSAR VU**

The regression equation from Step 2 is applied to the full VU raster to produce a spatially continuous map of predicted GWL change rate, exported as a GeoTIFF file.

**Step 4 — Compare observed vs predicted GWL change rate**

The observed GWL change rates at individual wells are plotted on top of the predicted GWL change rate map to validate the results.

<!-- Insert figure: observed GWL change rate points on predicted raster map -->
![Observed vs Predicted GWL change rate](figures/gwlcr_on_vu.png)

---

## Setup

This project runs in a conda environment. If you don't have conda installed, download [Miniconda](https://docs.conda.io/en/latest/miniconda.html) first.

**First time only — create the environment:**

```bash
source init_env.sh
```

This will automatically create the `gobi` conda environment from `environment.yml` and activate it.

**If the environment already exists:**

```bash
conda activate gobi
```

---

## File Structure

```
your_working_directory/
├── GOBI/                         # This repository
│   ├── scripts/
│   │   ├── get_vu.py
│   │   ├── gps_reference.py
│   │   ├── plot_ts.py
│   │   ├── plot_reg.py
│   │   ├── export_gwvel.py
│   │   ├── folium_map.py
│   │   ├── quick_plot.py
│   │   └── Address2Coord.py
│   ├── figures/                  # Figures for README
│   ├── environment.yml           # Conda environment
│   ├── init_env.sh               # Environment setup script
│   ├── gmt.conf
│   └── readme.md
├── data/                         # Input data (provided separately, not in repo)
└── outputs/                      # Output figures and maps
```

---

## Author

Lu Liang — School of GeoSciences, University of Edinburgh (2025–2026)
