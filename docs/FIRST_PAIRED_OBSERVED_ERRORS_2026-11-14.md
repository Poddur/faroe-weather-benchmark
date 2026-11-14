# First observed paired forecast errors — 14 November 2026

**Status: exploratory demonstration, NOT model-skill evidence.** All numbers calculated directly from the source artifacts of:
- [Matched ECMWF/HARMONIE run 43648017660](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43648017660), artifact ID **14134832048**, expiring **2026-11-28 22:27 UTC**.
- [DMI observational pilot run 43618246372](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43618246372), artifact ID **14122523629**, expiring **2026-11-28 16:55 UTC**.

## Provenance and validity

- Issue time: **2026-11-14 00:00 UTC** both forecast sources.
- Model valid times available: +6h 2026-11-14 06:00 UTC; +12h 2026-11-14 12:00 UTC; +24h 2026-11-15 00:00 UTC.
- DMI observations from the prior pilot exist for +6h and +12h, **not yet for +24h**.
- Three stations: 06009 Suður, 06011 Tórshavn, 06014 Eiði.
- Forecast source models: ECMWF IFS **0.25-degree** and HARMONIE DINI; variables are 2m temperature (C) and 10m wind speed (m/s).
- Archived bundle has 15 files: 9 ECMWF GRIB2, 3 HARMONIE station JSON, HARMONIE instance registry JSON, forecast CSV, provenance manifest JSON.
- **All 13 checksummed source files match** their manifest SHA-256 and byte-size records.
- Paired observation join: 24 forecast rows total (= 2 models x 3 stations x 2 variables x 2 valid times), or 12 observation/model pairs.
- No quality-controlled comparison against 0.1-degree ECMWF or independent long-term data has been performed.

## Mean absolute errors (MAE)

Each per-lead/model/variable MAE has **n=3 station observations**, insufficient for model superiority inference.

| Variable | Lead | ECMWF IFS MAE | HARMONIE DINI MAE | Unit |
|---|---:|---:|---:|---|
| temperature_2m | +6h | 1.207 | 0.666 | C |
| temperature_2m | +12h | 0.956 | 1.931 | C |
| wind_speed_10m | +6h | 4.406 | 1.306 | m/s |
| wind_speed_10m | +12h | 0.858 | 3.258 | m/s |

Pooled across +6 and +12 (n=6 each per model and variable): temperature ECMWF 1.081 C vs DINI 1.299 C; wind ECMWF 2.632 m/s vs DINI 2.282 m/s. These summaries pool horizons **only for descriptive purposes**, not as a statistical claim.

## Observation values (DMI)

| Station | 06 UTC temperature C | 12 UTC temperature C | 06 UTC wind m/s | 12 UTC wind m/s |
|---|---:|---:|---:|---:|
| 06009 Suður | 5.6 | 2.6 | 13.6 | 10.7 |
| 06011 Tórshavn | 3.6 | 2.4 | 13.0 | 11.1 |
| 06014 Eiði | 2.8 | 1.5 | 16.2 | 11.6 |

## Why this result is preliminary

1. One model issue and at most three stations per lead. Differences could be particular to this weather episode.
2. ECMWF used 0.25-degree nearest grid; DINI used much finer local grid.
3. Check 2m thermometer and 10m anemometer instrument heights plus wind averaging definition before formal scoring.
4. DMI observations are API raw observations, not necessarily final manually QC-verified records.
5. No statistical uncertainty intervals are meaningful for this small single-event sample.
6. Retain all primary artifact bytes **before 28 November 2026**, otherwise reproducibility depends on a vanished Actions artifact.

## Next steps

- Collect DMI observations for the 2026-11-15 00:00 UTC +24-hour verification timestamp.
- Run continuous contemporaneous archive collection for many independent weather episodes, with run ID and checksum preservation.
- Re-test with ECMWF 0.1-degree and potentially station-height adjustment; compare like for like.
- Only then conduct statistical significance and bias analyses.
