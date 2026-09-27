# Data card: Nepal cascade events (`cascades.csv`)

**Purpose.** A small, hand-curated table of Himalayan cascade events (a trigger leading to a
second, often larger, hazard). These events are **case studies, not a statistical sample**:
with n = 5 and three different process types, no copula or return period should ever be
fitted to them. The statistics in this repository use thousands of reported landslide days
instead (see `data/processed/unit_day.parquet`).

**Fields.** See `schema.json`. `rainfall_triggered` is `yes`, `partly` or `no`;
`verification_status` is `verified`, `partly verified`, `needs verification` or `provisional`.

**Rules.**
1. Every number carries its source in `key_sources`; conflicting estimates go in `notes`.
2. Fatality figures for events less than a year old are marked `provisional`.
3. Rows are only upgraded to `verified` after checking a peer-reviewed or official
   (NDRRMA, DHM, ICIMOD) source directly, not a news summary.

**Licence.** CC BY 4.0 for this table. Source datasets keep their own licences.

**Known gaps.** Official death tolls for Melamchi 2021 and Bhotekoshi 2025; final
post-event report for Rasuwa 2026; peak breach discharge for Jure (studies disagree).
