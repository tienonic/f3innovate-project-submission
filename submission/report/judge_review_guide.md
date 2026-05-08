# Review Guide

This is the fastest way to evaluate the submission without losing the main story in the file tree.

## Open In This Order

1. `submission/report/final_technical_report.pdf`
2. `submission/grower_quickstart.html`
3. `submission/tables/scouting_priority_table.csv`
4. `submission/figures/partner_site_1_report_zone_map.png`
5. `submission/figures/partner_site_1_canopy_priority_overlay.png`
6. `requirements_workspace/requirements_checklist.md`

## What To Look For

| Question | Where to check |
|---|---|
| Does it satisfy the F3 task? | `requirements_workspace/requirements_checklist.md` and the PDF executive summary. |
| Does it process every challenge boundary? | `submission/tables/spatial_zone_summary.csv` and the six-site map page in the PDF. |
| Does it use Sentinel-2 vegetation signals? | `submission/report/presentation_report.md` and `scripts/build_spatial_zones.py`. |
| Does it avoid non-canopy artifacts? | Canopy diagnostics, canopy/priority overlays, and verifier mask checks. |
| Is it reproducible? | `requirements_workspace/reproducibility.md`, `requirements_workspace/requirements.lock`, and `scripts/verify_submission_outputs.py`. |
| Is it useful to a grower or advisor? | `submission/grower_quickstart.html`, work orders, field feedback template, and validation sampling plan. |
| Is the refinement path honest? | The report section "How Additional Data Could Refine The Method" explains what extra records could add later without making causal claims in this run. |

## Review Read

This packet gives reviewers a complete pathway from imagery to field action:

- Open, reproducible Sentinel-2 L2A processing.
- Multi-season NDVI, NDMI, NDRE, and EVI2 evidence.
- Persistent canopy eligibility mask before baselines or scoring.
- Within-site baselines rather than universal thresholds.
- Six-site coverage with `partner_site_1` as the clearest orchard-specific example.
- Public-site caution instead of overclaiming mixed or unverified boundaries.
- CSV, GeoJSON, GeoTIFF, PNG, PDF, and HTML outputs.
- Grower quickstart, English/Spanish field brief, decision tree, work orders, centroids, and feedback labels.
- A clear refinement path for adding weather, ET, soil, terrain, and grower records later without turning the current product into a diagnosis tool.

## What This Does Not Claim

The maps do not diagnose disease, pest pressure, irrigation failure, soil problems, nutrient status, tissue status, yield loss, or cause. They identify persistent relative underperformance inside eligible canopy and convert that signal into a ranked scouting-priority workflow. Field verification is required before any agronomic conclusion.
