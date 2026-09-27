# Data folder

`raw/` and `processed/` are filled by the scripts and are not committed (see `.gitignore`).
Record the download date of each file here after running the scripts:

| File | Script | Downloaded on | Rows |
|---|---|---|---|
| raw/npl_adm2.geojson | 01 | 2026-09-26 | 77 districts (OCHA COD-AB v02, valid_on 2024-03-14; simplified 0.002 deg) |
| raw/bipad_landslide.csv | 02 | 2026-09-26 | 6,365 incidents (2011-05-14 to 2026-09-26; 6,373 fetched, 8 duplicate IDs dropped) |
| raw/coolr_nepal.csv | 03 | 2026-09-26 | 587 records (2007-2020; 665 in bbox, COOLR_Reports_Points) |
| raw/forcing_era5l.csv | 04 --product era5l | 2026-09-27 | 152,460 (77 districts x 1,980 days: JJAS + 10 lead days, 2011-2025); no gaps or duplicates |
| raw/forcing_imerg.csv | 04 --product imerg | 2026-09-27 | 152,460 (77 districts x 1,980 days, Nepal calendar days); no gaps or duplicates. Mean 10.3 mm/day vs ERA5-Land 13.4; Spearman r = 0.62 |

Download notes (2026-09-26)
- Boundaries: switched from geoBoundaries gbOpen to OCHA COD-AB (HDX). gbOpen NPL ADM2 has
  75 polygons with wrong names (Parsa and Siraha labelled Bara and Saptari, so two names
  are duplicated; Dailekh HQ falls in a polygon named Jajarkot; Rupandehi and Dailekh
  missing). COD-AB was checked with nine district HQ towns, all in the right polygon.
  All 6,365 BIPAD and 587 COOLR points fall in (or within 5 km of) a district.
- Forcing downloaded on the gbOpen polygons was discarded (kept in interim/old_geoboundaries/).
- BIPAD: season (JJAS) incidents rise from 57-122/yr in 2011-2015 to 243-934/yr in
  2021-2025. That is mostly reporting effort, and it lands on the train/test split.
- COOLR: the ArcGIS services moved from `/gis05/rest/` to `/portal/rest/` (config updated).
  586 of 587 records are from the NASA GLC, which effectively stops in 2018: there are
  no COOLR labels in the 2021-2025 test years. Location accuracy is 25 km or worse for
  about a third of records, so district assignment is uncertain for those.

`events/` holds the hand-curated cascade table and is committed.
