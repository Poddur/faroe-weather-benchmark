# DMI real observation availability — 14 November 2026

Evidence: manually dispatched GitHub Actions run [43616894967](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43616894967), job 132513811213, artifact **dmi-observation-availability-probe** (ID 14122047880). Data window 2026-11-13T16:40:46Z / 2026-11-14T16:40:46Z. All **28 API requests returned HTTP 200; 0 recorded request errors**. Total records returned: **1,650**. This is *record count*, not data-quality verification.

| Station ID | Station | temp_dry | wind_speed | pressure_at_sea | precip_past1h | total |
|---|---|---:|---:|---:|---:|---:|
|06007|Nolsoy|0|0|0|0|0|
|06008|Frodba Heliport|0|0|0|0|0|
|06009|Sudur|143|143|143|24|453|
|06011|Torshavn|143|143|143|24|453|
|06012|Fugloy|129|20|129|20|298|
|06013|Klaksvik Heliport|0|2|8|0|10|
|06014|Eidi|138|138|138|22|436|
|**Total**||**553**|**446**|**561**|**90**|**1650**|

- Selected for a **research-only raw-observation pilot**: 06009, 06011, 06014.
- Fugloy 06012 is an additional temperature/pressure candidate, not a full-coverage wind candidate in this specific day.
- Nolsoy 06007 and Frodba Heliport 06008 have no records in this 24-hour interval; cannot infer permanent station status.
- 10-minute and hourly records are mixed; a benchmark must align *valid times* and distinguish instantaneous vs accumulation observations.
- All returned observations had the probe's `quality_values={"unspecified":N}`. **This is because the probing code checks `properties.quality`; it does not establish whether DMI has quality flags elsewhere in its schema.**
- The probe counts all first-page features (maximum 1,000). This run showed no first-page truncation (all counts <1,000), but no long-term completeness determination is made.
- Verify actual parameter units and instrument (anemometer) height. `stationHeight` is elevation above sea level, **not** sensor height.
- For scientific benchmarking preserve source payloads, run issue time, raw data digests and station effective-dated metadata.

Next: manual observation-values pilot (not scheduled); then DMI-vs-ECMWF/HARMONIE temporal harmonization and raw archive design.
