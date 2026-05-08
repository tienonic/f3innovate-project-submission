# Persistent Orchard Underperformance Mapper

F3 Innovate Data Challenge #2: Satellite-Based Orchard Stress Mapping

- Solo submission: Nicholas Melnichenko, UC Davis
- Contact: think@ucdavis.edu
- GitHub: https://github.com/tienonic/f3innovate-project-submission
- Live field map: https://f3-orchard-stress-web.vercel.app

## What It Is

This submission is a grower scouting-priority tool. It uses Sentinel-2 L2A-derived NDVI, NDMI, NDRE, and EVI2 to flag eligible canopy areas that persistently underperform relative to the same site's own canopy baseline.

It is not a diagnosis tool. The map reduces the cognitive burden on growers and advisors: start with a ranked field signal, compare weak zones against stronger nearby canopy, check field memory and records, then verify cause in the field.

Field memory is always important. The goal is to add signal to what growers and advisors already know and make field follow-up easier to prioritize.

## Submission Map

| What to open | File |
|---|---|
| Final technical report | `submission/report/final_technical_report.pdf` |
| Review guide | `submission/report/judge_review_guide.md` |
| Grower quickstart webpage | `submission/grower_quickstart.html` |
| Live Vercel field map | https://f3-orchard-stress-web.vercel.app |
| Short presentation report | `submission/report/presentation_report.md` |
| Six-site summary table | `submission/tables/spatial_zone_summary.csv` |
| Zone-level scouting table | `submission/tables/scouting_priority_table.csv` |
| Grower work orders | `submission/report/grower_work_orders.md` |
| Grower work-order CSV | `submission/tables/grower_work_orders.csv` |
| Field feedback template | `submission/tables/field_verification_form_template.csv` |
| Validation sampling plan | `submission/tables/validation_sampling_plan.csv` |
| Six-site map overview | `submission/figures/spatial_zone_maps.png` |
| Kern 1 zoomed map | `submission/figures/kern_site_1_report_zone_map.png` |
| Stanislaus 1 visual public-site example | `submission/figures/stanislaus_site_1_report_zone_map.png` |
| Partner orchard map | `submission/figures/partner_site_1_report_zone_map.png` |
| Partner canopy/priority overlay | `submission/figures/partner_site_1_canopy_priority_overlay.png` |
| Requirement checklist | `requirements_workspace/requirements_checklist.md` |

The final PDF includes the review path through the work: method summary, six-site overview, partner-site detail, canopy-mask guardrail, trust/confidence explanation, partner-site zone evidence cards, a grower decision tree, a practical English/Spanish field brief, a field feedback loop, and a clear path for refining the method with grower or public context data later.

## What The Submission Does

The submission identifies canopy pixels that persistently underperform relative to the same site's own eligible-canopy baseline.

The output is built to help growers, PCAs, crop advisors, and field crews decide where to scout first. Field verification is required to determine cause. The submission is designed as one structured scouting signal inside existing grower/advisor practices, alongside field memory, PCA notes, irrigation records, management records, and local knowledge.

## Grower Quick Start

1. Open the site map: https://f3-orchard-stress-web.vercel.app.
2. Start with Scout first zones.
3. Compare each Scout first zone against a nearby Strong reference zone.
4. Check field memory, block maps, PCA notes, irrigation records, management records, and recent scouting notes.
5. Record what was found: confirmed concern, known context, no-action area, or needs revisit.
6. Do not assign cause from the satellite layer alone.

## How The Map Becomes Field Follow-Up

Field memory is always important. The tool reduces the cognitive burden on growers and advisors by adding one structured scouting signal to what they already know.

The field follow-up packet answers four questions: where to walk first, what to compare it against, what records to check, and what to write down after scouting.

Field feedback is used for threshold calibration next season, not as proof of disease, irrigation failure, soil problems, nutrient status, tissue status, or yield loss.

The grower quickstart webpage compresses the same workflow into a one-page decision tree with an English/Spanish toggle. It tells a field user where to look, what to compare, who should receive the observation, and how to label the feedback row for the next model run.

With grower records, the next version could be calibrated locally. Field scouting labels would tune thresholds; irrigation, variety, planting-age, and management records would explain expected differences; yield, packout, or quality observations would test whether persistent weak signals connect to outcomes the grower cares about.

## How Additional Data Could Refine The Method

The submitted product stays focused on Sentinel-2 canopy-limited persistent underperformance and scouting priority. I did not ingest CIMIS, ERA5, OpenET, SSURGO, DEM, yield, irrigation, pest, disease, tissue, or soil-lab datasets into this run.

If those data were available, I would add them after the canopy-priority layer as explanatory context, not as automatic diagnosis. For example, weather and ET records could help decide whether to review irrigation timing, SSURGO or soil tests could help decide whether mapped zones line up with known soil variability, DEM or slope could help identify drainage questions, and grower records could separate expected management differences from unexpected weak canopy signals.

The safe workflow would be: first map persistent canopy underperformance, then compare it with additional records, then send a scout to verify what is actually happening. Any added data would need clear dates, field boundaries, resolution notes, and grower context before it could refine confidence. It still would not turn satellite and public data alone into specific agronomic explanations or outcome claims.

## What Zone Classes Mean In The Field

| Zone class | Field meaning |
|---|---|
| Scout first | Visit first. Repeated weaker canopy signal inside eligible canopy. |
| Monitor | Check if nearby or if field time allows. Weaker or less persistent signal. |
| Stable | Use as normal context. No scouting priority from this signal alone. |
| Strong reference | Compare against this. Stronger within-site canopy signal. |

## What Is In This Repo

This GitHub repo is the final submission surface. It keeps the final deliverables and the code needed to reproduce them here, without the duplicate generated workbench files.

```text
submission/
  report/      final PDF and presentation markdown
  grower_quickstart.html
  tables/      scouting-priority, grower work-order, feedback, and summary CSVs
  figures/     final maps, canopy overlays, diagnostics, and charts
  geodata/     GeoJSON zones and GeoTIFF masks/rasters

requirements_workspace/
  requirements_checklist.md
  reproducibility.md
  requirements.lock
  environment.yml
  reference/

scripts/
  build_spatial_zones.py
  build_grower_work_orders.py
  build_visual_overlays.py
  build_final_report_pdf.py
  refresh_visual_assets.py
  sync_submission_assets.py
  verify_submission_outputs.py

data/
  geojsons/    six challenge boundary files
```

The repo intentionally does not commit `output/`. It is a local generated workbench created when the scripts are rerun. Committed final artifacts live in `submission/`.

## Six-Site Run

The submitted run covers all six challenge boundaries:

- `partner_site_1`
- `fresno_site_1`
- `kern_site_1`
- `kings_site_1`
- `stanislaus_site_1`
- `tulare_site_1`

`partner_site_1` is the strongest orchard-specific example. The public sites are included for full-boundary pipeline coverage and interpreted cautiously because crop and management context may be mixed or unverified.

Kern 1 (`kern_site_1`) is a useful small-boundary check: it has 19.62 eligible canopy acres and 0.00 scout-first acres. The public-facing map is zoomed so the tiny boundary signal is readable. It is presented as a conservative low-priority field-follow-up result, not a map failure.

`stanislaus_site_1` serves as a visually strong public-site example for inspecting how the map behaves across a complex landscape. It is still interpreted cautiously because crop and management context are unverified.

## Method Summary

1. Read the challenge GeoJSON site boundaries.
2. Search Sentinel-2 L2A scenes through public STAC providers.
3. Keep clear/valid observations and exclude invalid SCL classes when available.
4. Compute NDVI, NDMI, NDRE, and EVI2.
5. Build a multi-date persistent canopy/vegetation eligibility mask.
6. Compute within-site baselines only over eligible canopy pixels.
7. Score persistent multi-index underperformance relative to each site's own eligible-canopy distribution.
8. Export scouting-priority maps, canopy diagnostics, CSV tables, GeoJSON zones, GeoTIFF masks/rasters, and the final PDF.

## Current Results

| Site | Eligible canopy area | Images used | Scout first | Monitor | Stable | Strong reference |
|---|---:|---:|---:|---:|---:|---:|
| `partner_site_1` | 88.83 acres | 8 | 17.00 acres (19.14%) | 15.35 acres (17.27%) | 40.03 acres (45.06%) | 16.46 acres (18.53%) |
| `fresno_site_1` | 2,798.59 acres | 8 | 589.74 acres (21.07%) | 450.37 acres (16.09%) | 1,064.21 acres (38.03%) | 694.27 acres (24.81%) |
| `kern_site_1` | 19.62 acres | 8 | 0.00 acres (0.00%) | 0.22 acres (1.13%) | 17.57 acres (89.55%) | 1.83 acres (9.32%) |
| `kings_site_1` | 6,042.89 acres | 8 | 224.37 acres (3.71%) | 2,685.05 acres (44.43%) | 2,990.47 acres (49.49%) | 143.00 acres (2.37%) |
| `stanislaus_site_1` | 12,793.81 acres | 8 | 3,121.16 acres (24.40%) | 2,729.67 acres (21.34%) | 5,151.31 acres (40.26%) | 1,791.66 acres (14.00%) |
| `tulare_site_1` | 660.46 acres | 8 | 184.02 acres (27.86%) | 129.85 acres (19.66%) | 260.35 acres (39.42%) | 86.24 acres (13.06%) |

## Trust And Confidence

Confidence is an operational trust signal, not a causal claim. Stronger zones have enough clear Sentinel-2 observations, sit inside the persistent canopy mask, persist across years, and are supported by multiple indices. Public-boundary results are labeled cautious because crop and management context may be mixed or unverified.

The partner-site evidence cards in the PDF translate the map into a ranked field worklist. Each card reports area, persistence score, indices triggered, valid observation count, mean relative underperformance, centroid, and non-diagnostic field follow-up.

## Guardrails

- Do not use these maps to diagnose disease, pest pressure, irrigation failure, soil problems, nutrient status, tissue status, or yield loss.
- Non-canopy areas are excluded before baseline statistics and underperformance scoring.
- The workflow keeps the canopy mask, priority zones, maps, area calculations, and summary statistics canopy-limited.
- The scouting table recommends field follow-up rather than cause assignment.

## Reproduce Or Verify

PowerShell from the repo root:

```powershell
python -m pip install -r requirements_workspace\requirements.lock
python scripts\build_spatial_zones.py --sites all
python scripts\build_visual_overlays.py
python scripts\build_final_report_pdf.py --figures-dir submission\figures --spatial-dir submission\tables --output submission\report\final_technical_report.pdf
python scripts\build_grower_work_orders.py
python scripts\build_grower_quickstart_page.py
python scripts\verify_submission_outputs.py
```

The verification script checks the committed `submission/` packet, including all six sites, required tables, per-site maps and diagnostics, the standalone quickstart webpage, machine-readable canopy/underperformance masks, and non-diagnostic report language.

## Keep Maps In Sync

`submission/figures` is the source of truth for GitHub, the final PDF, and the Obsidian visual report. If one site map changes, run this from the repo root:

```powershell
python scripts\refresh_visual_assets.py
```

That rebuilds the current visual overlays, regenerates the final PDF, rebuilds the grower work-order artifacts, rebuilds the quickstart webpage, copies the current figures into the Obsidian F3 project, and runs the verifier. Use this before judging or printing so Kern 1 and the other site maps are not stale in downstream copies.

`refresh_visual_assets.py` assumes `output/spatial` corresponds to the current submitted tables and geodata unless a full spatial rebuild and submission sync has also been performed.
