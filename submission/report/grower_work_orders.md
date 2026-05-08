# Grower Work Orders

This is a scouting-priority field worklist, not a diagnosis tool. It turns the submitted maps and scouting-priority zones into starting coordinates, comparison prompts, records checks, and a simple field-feedback loop.

Use these coordinates as field navigation prompts, not routes. The repo does not include rows, gates, roads, irrigation sets, or access lanes.

Planning estimate formula: estimated_visit_minutes = 12 base minutes + 4 minutes per acre, bounded from 12 to 45 minutes for a first-pass scouting stop. These are planning estimates, not true labor costs.

## Decision Rules

- Send scout: Scout first zone, especially high persistence and multi-index agreement.
- Compare: always compare Scout first and Monitor zones to nearby Strong reference areas or stable canopy.
- Inspect: note visible canopy difference, irrigation distribution signs, pest or disease symptoms, and soil or water movement signs.
- Call PCA/crop advisor/irrigation tech: only if field symptoms or records support follow-up.
- Monitor/no action: use when a Monitor zone has no visible difference, known benign context, or insufficient access/time.

## Operational Feedback Metrics

- confirmed_useful_rate = visited Scout first/Monitor zones labeled confirmed_useful or known_context divided by visited Scout first/Monitor zones.
- false_alert_rate = visited Scout first/Monitor zones labeled no_action divided by visited Scout first/Monitor zones.
- reference_agreement_rate = visited Strong reference zones that looked normal/strong relative to Scout first zones divided by visited Strong reference zones.
- missed_signal_check = Stable/Strong reference samples where a visible concern was found; use these to review thresholds or canopy mask behavior next season.

This is a low-burden operational feedback loop, not a full statistical accuracy assessment.

## Site Work Orders

### partner_site_1 - Partner Site 1 orchard-specific example

Eligible canopy: 88.83 acres; images used: 8; Scout first: 17.00 acres (19.14%); Monitor: 15.35 acres; Stable: 40.03 acres; Strong reference: 16.46 acres. Partner Site 1 is the clearest orchard-specific example in this packet.

Map file to open: `submission/figures/partner_site_1_report_zone_map.png`.

Top zones to walk first:

| Rank | Zone | Class | Acres | Persistence | Starting coordinate | Est. minutes |
|---:|---|---|---:|---:|---|---:|
| 1 | `partner_site_1_priority_022` | Scout first | 0.32 | 1.00 | 36.6081358, -119.4965109 | 13 |
| 2 | `partner_site_1_priority_002` | Scout first | 0.07 | 1.00 | 36.6111708, -119.5021984 | 12 |
| 3 | `partner_site_1_priority_025` | Scout first | 1.38 | 0.97 | 36.6075198, -119.4984853 | 18 |
| 4 | `partner_site_1_priority_004` | Scout first | 0.35 | 0.96 | 36.6109964, -119.5019213 | 13 |
| 5 | `partner_site_1_priority_021` | Scout first | 9.56 | 0.91 | 36.6100392, -119.4987394 | 45 |

What to compare against: Strong reference starting coordinate: 36.6083287, -119.5000147. Compare the zone against Strong reference or stable canopy before deciding follow-up.

Records to check: field memory; block map; recent scouting notes; irrigation set records; PCA or crop-advisor notes; management records.

Field observations to make: visible canopy difference; irrigation distribution observation; pest or disease symptom observation; soil or water movement observation; photos if useful.

What to write down after scouting: actual minutes; visible difference yes/no/unclear; records checked; photos taken; finding_label; followup_owner only if field symptoms or records support follow-up.

This work order does not assign cause from satellite imagery.

### fresno_site_1 - Fresno Site 1 public boundary - cautious interpretation

Eligible canopy: 2798.59 acres; images used: 8; Scout first: 589.74 acres (21.07%); Monitor: 450.37 acres; Stable: 1064.21 acres; Strong reference: 694.27 acres. This is a public boundary; interpret the work order cautiously because crop and management context are unverified.

Map file to open: `submission/figures/fresno_site_1_report_zone_map.png`.

Top zones to walk first:

| Rank | Zone | Class | Acres | Persistence | Starting coordinate | Est. minutes |
|---:|---|---|---:|---:|---|---:|
| 1 | `fresno_site_1_priority_136` | Scout first | 5.96 | 1.00 | 36.4556872, -119.8118498 | 36 |
| 2 | `fresno_site_1_priority_118` | Scout first | 4.67 | 1.00 | 36.4564320, -119.8135421 | 31 |
| 3 | `fresno_site_1_priority_610` | Scout first | 1.36 | 1.00 | 36.4305656, -119.8029906 | 17 |
| 4 | `fresno_site_1_priority_371` | Scout first | 1.33 | 1.00 | 36.4396912, -119.7890959 | 17 |
| 5 | `fresno_site_1_priority_847` | Scout first | 1.26 | 1.00 | 36.4227887, -119.7900621 | 17 |

What to compare against: Strong reference starting coordinate: 36.4563134, -119.7925509. Compare the zone against Strong reference or stable canopy before deciding follow-up.

Records to check: field memory and records if available; public-boundary context; avoid inferring crop or management history.

Field observations to make: visible canopy difference; irrigation distribution observation; pest or disease symptom observation; soil or water movement observation; photos if useful.

What to write down after scouting: actual minutes; visible difference yes/no/unclear; records checked; photos taken; finding_label; followup_owner only if field symptoms or records support follow-up.

This work order does not assign cause from satellite imagery.

### kern_site_1 - Kern Site 1 small-boundary low-priority result

Eligible canopy: 19.62 acres; images used: 8; Scout first: 0.00 acres (0.00%); Monitor: 0.22 acres; Stable: 17.57 acres; Strong reference: 1.83 acres. Kern Site 1 is a small-boundary low-priority result, not necessarily a failed map: 19.62 eligible canopy acres and 0.00 Scout first acres.

Map file to open: `submission/figures/kern_site_1_report_zone_map.png`.

No Scout first zones were found for Kern Site 1. Treat this as a conservative low-priority check, not a failed result.

Top zones to walk first:

| Rank | Zone | Class | Acres | Persistence | Starting coordinate | Est. minutes |
|---:|---|---|---:|---:|---|---:|
| 1 | `kern_site_1_priority_001` | Monitor | 0.22 | 0.28 | 35.4528827, -119.0449844 | 13 |
| 2 | `kern_site_1_strong_reference_063` | Strong reference | 0.47 | 0.00 | 35.4542882, -119.0391863 | 14 |
| 3 | `kern_site_1_stable_090` | Stable | 1.09 | 0.10 | 35.4524804, -119.0294954 | 16 |

What to compare against: Strong reference starting coordinate: 35.4542882, -119.0391863. Compare the zone against Strong reference or stable canopy before deciding follow-up.

Records to check: field memory and records if available; public-boundary context; avoid inferring crop or management history.

Field observations to make: visible canopy difference; irrigation distribution observation; pest or disease symptom observation; soil or water movement observation; photos if useful.

What to write down after scouting: actual minutes; visible difference yes/no/unclear; records checked; photos taken; finding_label; followup_owner only if field symptoms or records support follow-up.

This work order does not assign cause from satellite imagery.

### kings_site_1 - Kings Site 1 public boundary - cautious interpretation

Eligible canopy: 6042.89 acres; images used: 8; Scout first: 224.37 acres (3.71%); Monitor: 2685.05 acres; Stable: 2990.47 acres; Strong reference: 143.00 acres. This is a public boundary; interpret the work order cautiously because crop and management context are unverified.

Map file to open: `submission/figures/kings_site_1_report_zone_map.png`.

Top zones to walk first:

| Rank | Zone | Class | Acres | Persistence | Starting coordinate | Est. minutes |
|---:|---|---|---:|---:|---|---:|
| 1 | `kings_site_1_priority_669` | Scout first | 0.12 | 1.00 | 36.0430460, -119.6451589 | 12 |
| 2 | `kings_site_1_priority_679` | Scout first | 0.05 | 1.00 | 36.0427825, -119.6447596 | 12 |
| 3 | `kings_site_1_priority_673` | Scout first | 0.03 | 1.00 | 36.0428771, -119.6449220 | 12 |
| 4 | `kings_site_1_priority_685` | Scout first | 0.07 | 0.78 | 36.0426557, -119.6445246 | 12 |
| 5 | `kings_site_1_priority_660` | Scout first | 0.05 | 0.75 | 36.0424132, -119.6076613 | 12 |

What to compare against: Strong reference starting coordinate: 36.0760893, -119.5942842. Compare the zone against Strong reference or stable canopy before deciding follow-up.

Records to check: field memory and records if available; public-boundary context; avoid inferring crop or management history.

Field observations to make: visible canopy difference; irrigation distribution observation; pest or disease symptom observation; soil or water movement observation; photos if useful.

What to write down after scouting: actual minutes; visible difference yes/no/unclear; records checked; photos taken; finding_label; followup_owner only if field symptoms or records support follow-up.

This work order does not assign cause from satellite imagery.

### stanislaus_site_1 - Stanislaus Site 1 public boundary - cautious interpretation

Eligible canopy: 12793.81 acres; images used: 8; Scout first: 3121.16 acres (24.40%); Monitor: 2729.67 acres; Stable: 5151.31 acres; Strong reference: 1791.66 acres. This is a public boundary; interpret the work order cautiously because crop and management context are unverified.

Map file to open: `submission/figures/stanislaus_site_1_report_zone_map.png`.

Top zones to walk first:

| Rank | Zone | Class | Acres | Persistence | Starting coordinate | Est. minutes |
|---:|---|---|---:|---:|---|---:|
| 1 | `stanislaus_site_1_priority_4268` | Scout first | 5.83 | 1.00 | 37.3203375, -120.7808654 | 35 |
| 2 | `stanislaus_site_1_priority_4236` | Scout first | 4.72 | 1.00 | 37.3210990, -120.7810482 | 31 |
| 3 | `stanislaus_site_1_priority_3953` | Scout first | 4.37 | 1.00 | 37.3304139, -120.7985037 | 29 |
| 4 | `stanislaus_site_1_priority_3329` | Scout first | 3.73 | 1.00 | 37.3457700, -120.8214789 | 27 |
| 5 | `stanislaus_site_1_priority_3355` | Scout first | 3.16 | 1.00 | 37.3449456, -120.8218101 | 25 |

What to compare against: Strong reference starting coordinate: 37.3301284, -120.8166235. Compare the zone against Strong reference or stable canopy before deciding follow-up.

Records to check: field memory and records if available; public-boundary context; avoid inferring crop or management history.

Field observations to make: visible canopy difference; irrigation distribution observation; pest or disease symptom observation; soil or water movement observation; photos if useful.

What to write down after scouting: actual minutes; visible difference yes/no/unclear; records checked; photos taken; finding_label; followup_owner only if field symptoms or records support follow-up.

This work order does not assign cause from satellite imagery.

### tulare_site_1 - Tulare Site 1 public boundary - cautious interpretation

Eligible canopy: 660.46 acres; images used: 8; Scout first: 184.02 acres (27.86%); Monitor: 129.85 acres; Stable: 260.35 acres; Strong reference: 86.24 acres. This is a public boundary; interpret the work order cautiously because crop and management context are unverified.

Map file to open: `submission/figures/tulare_site_1_report_zone_map.png`.

Top zones to walk first:

| Rank | Zone | Class | Acres | Persistence | Starting coordinate | Est. minutes |
|---:|---|---|---:|---:|---|---:|
| 1 | `tulare_site_1_priority_006` | Scout first | 0.77 | 1.00 | 36.1249855, -119.1601962 | 15 |
| 2 | `tulare_site_1_priority_016` | Scout first | 0.15 | 1.00 | 36.1242346, -119.1564740 | 13 |
| 3 | `tulare_site_1_priority_021` | Scout first | 0.12 | 1.00 | 36.1241476, -119.1569641 | 12 |
| 4 | `tulare_site_1_priority_003` | Scout first | 0.05 | 1.00 | 36.1251107, -119.1545351 | 12 |
| 5 | `tulare_site_1_priority_108` | Scout first | 0.05 | 1.00 | 36.1224612, -119.1439635 | 12 |

What to compare against: Strong reference starting coordinate: 36.1213431, -119.1758402. Compare the zone against Strong reference or stable canopy before deciding follow-up.

Records to check: field memory and records if available; public-boundary context; avoid inferring crop or management history.

Field observations to make: visible canopy difference; irrigation distribution observation; pest or disease symptom observation; soil or water movement observation; photos if useful.

What to write down after scouting: actual minutes; visible difference yes/no/unclear; records checked; photos taken; finding_label; followup_owner only if field symptoms or records support follow-up.

This work order does not assign cause from satellite imagery.
