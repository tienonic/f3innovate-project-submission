# Requirements Checklist

This checklist compares the current repository against the F3 Innovate Data Challenge #2 submission requirements for the Persistent Orchard Underperformance Mapper.

## Verdict

Status: final-ready after regenerated visual layout review and review-path check.

The pipeline and generated outputs meet the requested six-site, canopy-limited, non-diagnostic scouting-priority framing. The final PDF pages and regenerated map figures were rendered for a visual overlap pass after the last layout refinement. The README, review guide, and final PDF show the review path through the submitted artifacts.

## Requirement Status

| Requirement | Status | Evidence |
|---|---|---|
| Inspect repo and identify site list | Met | `../scripts/build_spatial_zones.py` defines all six site IDs and accepts `--sites all`. |
| Process all six boundaries | Met | `../submission/tables/spatial_zone_summary.csv` includes `fresno_site_1`, `kern_site_1`, `kings_site_1`, `partner_site_1`, `stanislaus_site_1`, and `tulare_site_1`. |
| Use Sentinel-2 L2A-derived NDVI, NDMI, NDRE, and EVI2 | Met | Method summary in `../submission/report/presentation_report.md`; implementation in `../scripts/build_spatial_zones.py`. |
| Keep `partner_site_1` as strongest orchard-specific example | Met | `../submission/README.md` puts `partner_site_1` first; PDF and report text frame it as the clearest orchard-specific example. |
| Treat public sites cautiously | Met | PDF, README, and presentation report state that public-site crop and management context may be mixed or unverified. |
| Avoid diagnosis claims | Met | Verification checks report/source text for diagnostic overclaiming; current framing says field verification is required to determine cause. |
| Persistent canopy/vegetation eligibility mask | Met | Per-site masks are exported in `../submission/geodata/`; diagnostics are exported in `../submission/figures/*_canopy_mask_diagnostic.png`. |
| Use clear/valid observations and SCL exclusions when available | Met | Implemented in `../scripts/build_spatial_zones.py`; summarized in `../submission/report/presentation_report.md`. |
| Build canopy mask from multi-date vegetation evidence | Met | Mask uses valid observation count plus NDVI/EVI2 distribution thresholds; thresholds are recorded in `../submission/geodata/methodology_notes.json`. |
| Apply canopy mask before scoring | Met | Baselines, masks, zones, acreage, maps, and summaries are canopy-limited. Verifier checks masks and outputs. |
| Verify no priority pixels outside canopy | Met | `python scripts\verify_submission_outputs.py` checks underperformance, zone, and score rasters against canopy masks. |
| Prevent roads/non-canopy areas from being labeled | Met | Canopy mask removes non-canopy pixels before scoring; overlays in `../submission/figures/*_canopy_priority_overlay.png` show priority colors clipped to canopy. |
| Crop/zoom final figures | Met | Site report maps are generated as per-site cropped figures in `../submission/figures/*_report_zone_map.png`; Kern 1 is zoomed further because the public boundary signal is tiny in the six-site overview. |
| Include all six sites in final PDF | Met | `../submission/report/final_technical_report.pdf` includes all six sites and a six-site summary table. |
| Add grower workflow and limitations | Met | PDF, README, webpage, and presentation report include scouting workflow and limitations. |
| Add low-cognitive-burden grower quick start | Met | README, submission README, presentation report, PDF, and `../submission/grower_quickstart.html` explain where to start, what to compare against, which records to check, what to record, and what not to conclude. |
| Add grower decision tree and Spanish option | Met | `../submission/report/final_technical_report.pdf` and `../submission/grower_quickstart.html` include a decision tree, practical field brief, and English/Spanish field-facing quickstart. |
| Add manual-verification feedback loop | Met | `../submission/tables/field_verification_form_template.csv`, `../submission/tables/validation_sampling_plan.csv`, the PDF, and webpage describe how confirmed concern, known context, no action, revisit later, and missed-signal checks feed threshold calibration. |
| Add confidence/trust interpretation | Met | PDF and presentation report include operational confidence, partner-site zone evidence cards, and Kern small-boundary interpretation. |
| Add scouting-priority output table | Met | `../submission/tables/scouting_priority_table.csv` includes site, zone, area, persistence, triggered indices, valid observations, relative underperformance, centroid, and follow-up guidance. |
| Add verification script | Met | `../scripts/verify_submission_outputs.py` checks required artifacts, all six sites, masks, links, stale text, and report language. |
| Keep implementation reproducible and explainable | Met | `reproducibility.md`, minimal dependencies, transparent index logic, and no black-box model. |
| Add review path | Met | `../submission/report/judge_review_guide.md`, README Submission Map table, and final PDF review path show what to inspect first. |
| Address public F3 judging criteria | Met | Final report, review guide, and checklist map the packet to technical quality, methodology/reproducibility, grower applicability, and communication. |
| Explain future refinement path | Met | README and final report explain how weather, ET, soil, terrain, and grower records could refine confidence later without assigning cause from satellite data alone. |

## What Was Actually Built

- Six-site Sentinel-2 L2A processing pipeline.
- Clear-pixel and SCL filtering.
- Multi-date canopy/vegetation eligibility mask.
- Within-site baseline comparison over eligible canopy only.
- Persistent multi-index underperformance scoring.
- Cropped per-site maps and canopy diagnostics.
- Final technical PDF report.
- Standalone grower quickstart webpage with embedded map visuals and English/Spanish toggle.
- CSV scouting-priority table.
- GeoJSON zones and GeoTIFF masks/rasters.
- Local verification script.

## Steering Notes

- This is not a diagnosis tool. The report should keep using scouting-priority, persistent underperformance, field follow-up, and grower triage language.
- `partner_site_1` is the cleanest orchard-specific example but still is not ground truth.
- Public sites show full-boundary pipeline coverage; interpretation is cautious because crop context may be mixed or unverified.
- The submission is structured to be usable beyond a PDF: CSV for spreadsheet workflows, GeoJSON for GIS, GeoTIFF for reproducible spatial layers, and PDF for review.

## Optional Final Polish

- If a review ZIP is created, include `submission/`, `requirements_workspace/`, `scripts/`, and `data/`. Do not include the local generated `output/` workbench or private/support-note folders.
