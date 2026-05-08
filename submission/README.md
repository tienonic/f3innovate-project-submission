# My Final Submission Packet

Solo submission: Nicholas Melnichenko, UC Davis
Contact: think@ucdavis.edu
Live field map: https://f3-orchard-stress-web.vercel.app

## What It Is

My submission is a grower scouting-priority tool. It flags eligible canopy areas that persistently underperform relative to the same site's own canopy baseline. It is not a diagnosis tool.

I use the map to reduce the cognitive burden on growers and advisors: start with a ranked field signal, compare weak zones against stronger nearby canopy, check field memory and records, then verify cause in the field.

Field memory is always important. My goal is to add signal to what growers and advisors already know and make field follow-up easier to prioritize.

## Submission Map

| Item | File |
|---|---|
| Final technical report | `report/final_technical_report.pdf` |
| Judge review guide | `report/judge_review_guide.md` |
| Grower quickstart webpage | `grower_quickstart.html` |
| Live Vercel field map | https://f3-orchard-stress-web.vercel.app |
| Presentation report | `report/presentation_report.md` |
| Grower work orders | `report/grower_work_orders.md` |
| Scouting-priority table | `tables/scouting_priority_table.csv` |
| Grower work-order table | `tables/grower_work_orders.csv` |
| Field feedback template | `tables/field_verification_form_template.csv` |
| Validation sampling plan | `tables/validation_sampling_plan.csv` |
| Six-site summary table | `tables/spatial_zone_summary.csv` |
| Strong-reference versus priority time series | `tables/zone_timeseries_all_sites.csv` |

My PDF includes the main judge-facing story: challenge-fit scorecard, six-site coverage, partner-site detail, canopy-mask guardrail, trust/confidence interpretation, partner-site zone evidence cards, a grower decision tree, a practical English/Spanish field brief, and a feedback loop from map to field follow-up.

## Grower Quick Start

1. Open the site map.
2. Start with Scout first zones.
3. Compare each Scout first zone against a nearby Strong reference zone.
4. Check field memory, block maps, PCA notes, irrigation records, management records, and recent scouting notes.
5. Record what was found: confirmed concern, known context, no-action area, or needs revisit.
6. Do not assign cause from the satellite layer alone.

## How The Map Becomes Field Follow-Up

Field memory is always important. I am trying to reduce the cognitive burden on growers and advisors by adding one structured scouting signal to what they already know.

My field follow-up packet answers four questions: where to walk first, what to compare it against, what records to check, and what to write down after scouting.

Field feedback is used for threshold calibration next season, not as proof of disease, irrigation failure, soil problems, nutrient status, tissue status, or yield loss.

My grower quickstart webpage is the short field-facing version: one-page decision tree, zone-class key, who-receives-what guidance, embedded map visuals, and an English/Spanish toggle.

My refinement path is practical: scouting labels tune thresholds, management and irrigation records explain expected differences, and yield or quality observations test whether repeated weak signals connect to outcomes the grower cares about.

## What Zone Classes Mean In The Field

| Zone class | Field meaning |
|---|---|
| Scout first | Visit first. Repeated weaker canopy signal inside eligible canopy. |
| Monitor | Check if nearby or if field time allows. Weaker or less persistent signal. |
| Stable | Use as normal context. No scouting priority from this signal alone. |
| Strong reference | Compare against this. Stronger within-site canopy signal. |

## Key Figures

| Site | Main map | Canopy/priority overlay | Canopy diagnostic | Time series |
|---|---|---|---|---|
| `partner_site_1` | `figures/partner_site_1_report_zone_map.png` | `figures/partner_site_1_canopy_priority_overlay.png` | `figures/partner_site_1_canopy_mask_diagnostic.png` | `figures/partner_site_1_zone_timeseries.png` |
| `fresno_site_1` | `figures/fresno_site_1_report_zone_map.png` | `figures/fresno_site_1_canopy_priority_overlay.png` | `figures/fresno_site_1_canopy_mask_diagnostic.png` | `figures/fresno_site_1_zone_timeseries.png` |
| `kern_site_1` | `figures/kern_site_1_report_zone_map.png` | `figures/kern_site_1_canopy_priority_overlay.png` | `figures/kern_site_1_canopy_mask_diagnostic.png` | `figures/kern_site_1_zone_timeseries.png` |
| `kings_site_1` | `figures/kings_site_1_report_zone_map.png` | `figures/kings_site_1_canopy_priority_overlay.png` | `figures/kings_site_1_canopy_mask_diagnostic.png` | `figures/kings_site_1_zone_timeseries.png` |
| `stanislaus_site_1` | `figures/stanislaus_site_1_report_zone_map.png` | `figures/stanislaus_site_1_canopy_priority_overlay.png` | `figures/stanislaus_site_1_canopy_mask_diagnostic.png` | `figures/stanislaus_site_1_zone_timeseries.png` |
| `tulare_site_1` | `figures/tulare_site_1_report_zone_map.png` | `figures/tulare_site_1_canopy_priority_overlay.png` | `figures/tulare_site_1_canopy_mask_diagnostic.png` | `figures/tulare_site_1_zone_timeseries.png` |

I include the six-site overview at `figures/spatial_zone_maps.png` and the pipeline diagram at `figures/pipeline_diagram.png`.

Direct visual checks worth opening:

- Kern 1 zoomed map: `figures/kern_site_1_report_zone_map.png`
- Stanislaus 1 visual public-site example: `figures/stanislaus_site_1_report_zone_map.png`
- Partner orchard-specific example: `figures/partner_site_1_report_zone_map.png`

## Machine-Readable Outputs

For each site, `geodata/` includes:

- `*_zones.geojson`: vector scouting-priority zones.
- `*_zones.tif`: zone class raster.
- `*_canopy_mask.tif`: persistent canopy/vegetation eligibility mask.
- `*_underperformance_mask.tif`: binary persistent underperformance mask.
- `*_underperformance_score.tif`: canopy-limited underperformance score.
- `*_valid_observation_count.tif`: valid clear-observation count.

## Interpretation

I use `partner_site_1` as the clearest orchard-specific example. I include the public sites for full-boundary pipeline coverage, and I interpret them cautiously because crop and management context may be mixed or unverified.

Kern 1 (`kern_site_1`) is a small-boundary check with 19.62 eligible canopy acres and 0.00 scout-first acres. I zoomed its map for readability because the boundary is tiny in the six-site overview. I include it to show that the pipeline can return a conservative low-priority result instead of forcing a dramatic map.

I use `stanislaus_site_1` as the most visually rich public-site figure. It is useful for presentation and inspection, but I keep it as a cautious interpretation because crop and management context are unverified.

Confidence is an operational trust signal, not a diagnosis. Stronger zones have enough clear observations, sit inside the persistent canopy mask, persist across years, and show multi-index agreement. I keep public-site confidence bounded by the lack of verified crop and management context.

Use these maps to prioritize scouting. Field verification is required to determine cause.

## Refresh Rule

I use the root repo command `python scripts\refresh_visual_assets.py` as the dependency path for visual outputs and grower work-order artifacts. It rebuilds the current maps and PDF, rebuilds the work orders and field feedback templates, builds the standalone grower quickstart webpage, then syncs the same figures into the Obsidian project so GitHub and the final report use the same current images.
