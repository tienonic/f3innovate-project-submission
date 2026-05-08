# Reproducibility

## Clean Environment

Use either `requirements_workspace\requirements.lock` with pip or `requirements_workspace\environment.yml` with conda/mamba. The lock file is intentionally minimal and does not include the author's full workstation environment.

PowerShell setup with pip:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements_workspace\requirements.lock
```

Conda setup:

```powershell
conda env create -f requirements_workspace\environment.yml
conda activate f3-orchard-stress
```

## Rebuild Command

Run from the release folder root:

```powershell
python scripts\build_spatial_zones.py --sites all
```

Build the PDF report after spatial outputs are present:

```powershell
python scripts\build_final_report_pdf.py --figures-dir submission\figures --spatial-dir submission\tables --output submission\report\final_technical_report.pdf
```

Build the grower work orders and field feedback templates from the submitted tables and GeoJSON zones:

```powershell
python scripts\build_grower_work_orders.py
```

Build the standalone grower quickstart webpage with embedded map visuals:

```powershell
python scripts\build_grower_quickstart_page.py
```

Refresh the committed visuals, final PDF, and Obsidian copies from the current spatial outputs:

```powershell
python scripts\refresh_visual_assets.py
```

Use the refresh command after changing any per-site map logic. `submission/figures` is treated as the source of truth for GitHub, the final report, and local presentation materials.

`refresh_visual_assets.py` assumes `output/spatial` corresponds to the current submitted tables and geodata unless a full spatial rebuild and submission sync has also been performed.

## Expected Outputs

- `output/figures/spatial_zone_maps.png`
- `output/figures/*_stress_zones.png`
- `output/figures/*_report_zone_map.png`
- `output/figures/*_canopy_priority_overlay.png`
- `output/figures/*_canopy_mask_diagnostic.png`
- `output/figures/*_zone_timeseries.png`
- `output/spatial/*_canopy_mask.tif`
- `output/spatial/*_underperformance_mask.tif`
- `output/spatial/*_zones.tif`
- `output/spatial/*_zones.geojson`
- `output/spatial/*_underperformance_score.tif`
- `output/spatial/*_confidence.tif`
- `output/spatial/spatial_zone_summary.csv`
- `output/spatial/zone_timeseries_all_sites.csv`
- `output/spatial/methodology_notes.json`
- `submission/report/final_technical_report.pdf`
- `submission/grower_quickstart.html`
- `submission/report/grower_work_orders.md`
- `submission/tables/scouting_priority_table.csv`
- `submission/tables/grower_work_orders.csv`
- `submission/tables/field_verification_form_template.csv`
- `submission/tables/validation_sampling_plan.csv`
- `submission/figures/*_report_zone_map.png`
- `submission/figures/*_canopy_priority_overlay.png`
- `submission/geodata/*_zones.geojson`

## External Services

The rebuild requires outbound HTTPS access to Microsoft Planetary Computer:

- `https://earth-search.aws.element84.com/v1/search`
- `https://planetarycomputer.microsoft.com/api/stac/v1/search`
- `https://planetarycomputer.microsoft.com/api/sas/v1/sign`

No Earth Engine account or Google credential is required for the submitted pipeline.

## Known Runtime Notes

The latest spatial rebuild completed successfully for all six challenge boundaries. The pipeline tries Earth Search first and can fall back to Planetary Computer. Sparse-data warnings for all-NaN slices can appear in masked imagery; they do not prevent output generation.
