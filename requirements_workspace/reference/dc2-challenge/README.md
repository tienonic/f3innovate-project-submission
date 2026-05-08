# Data — Satellite-Based Orchard Stress Mapping Challenge

This folder contains geospatial boundary files for orchard sites used in the F3 Innovate Data Challenge: **Satellite-Based Orchard Stress Mapping**.

Unlike traditional challenges, no single precompiled dataset is provided. Participants are expected to build pipelines to access, process, and analyze satellite imagery directly.

---

## Folder Structure

## Site Data

Each `.geojson` file defines a **region of interest (ROI)** corresponding to an orchard site in California’s Central Valley.

### Public Sites
- Represent typical orchard regions across different geographies and crop types
- Intended for method development, testing, and benchmarking

### Partner Site
- `partner_site_1.geojson`
- Represents a real-world orchard boundary provided in collaboration with an industry partner
- May include greater complexity (e.g., mixed varieties, smaller blocks, irregular structure)
- Intended as a realistic test case for applying your pipeline

---

## Data Access

Participants will use these site boundaries to query satellite imagery, primarily:

- **Sentinel-2 multispectral imagery**

From this imagery, participants are expected to derive vegetation indices such as:

- NDVI (Normalized Difference Vegetation Index)
- NDMI (Moisture Index)
- NDRE (Red-edge Index)
- EVI (Enhanced Vegetation Index)

---

## Recommended Workflow

A typical workflow includes:

1. Load a site boundary (`.geojson`)
2. Extract the bounding box (ROI)
3. Query Sentinel-2 imagery for that region
4. Apply cloud masking and filtering
5. Compute vegetation indices
6. Aggregate multi-season time series
7. Analyze spatial variability
8. Generate maps and insights

---

## Data Guidelines

- All analysis must use **open-source or publicly accessible datasets**
- Pipelines must be **fully reproducible**
- Participants are encouraged to test across **multiple sites**
- The partner site should be included as part of your analysis

---

## Usage Notes

- Site boundaries are provided for **research and educational use within this challenge only**
- Do not redistribute these files outside the context of the challenge
- Results should be interpreted as **relative spatial variability**, not definitive diagnosis of field conditions

---

## Coordinate System

All GeoJSON files are provided in:

- `EPSG:4326` (WGS84 latitude / longitude)
