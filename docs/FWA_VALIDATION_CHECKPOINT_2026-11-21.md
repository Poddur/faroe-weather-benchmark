# FWA validation checkpoint — 2026-11-21 (UTC)

## Purpose and freeze
Read-only scientific audit of previously collected outcomes, against repository main as inspected through commit `620f92d7e` (2026-11-21 03:57:20 UTC). No model coefficients, algorithms, datasets, score calculations or collection schedules changed by this checkpoint. Preserve frozen native FWA v1 and geographic v2 separately and never fit on their prospective observations.

## Operational archive: verified
- Last recorded success: `ops/latest_success.json` updated 2026-11-20 22:46:52 UTC; HARMONIE/ECMWF issue 2026-11-20 00Z, 36 forecast records and 532 observation records; [run 44831190627](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/44831190627), scheduled, success.
- Earlier scheduled archive [run 44743020714](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/44743020714) failed; an open operational tracker [issue #3](https://github.com/Poddur/faroe-weather-benchmark/issues/3) exists. One success does not prove zero future schedule gaps.
- The dense workflow `.github/workflows/fwa-dense-regimes.yml` is scheduled daily at 16:31 UTC and predeclares previous-day 00Z HARMONIE with +6/+12/+18/+24 h, without selecting only storm cases. Latest stored receipt `ops/fwa_geo_dense_latest.json` states all four leads complete, 36 rows and success in [run 44863379388](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/44863379388).
- The geographic v2 and prospective v1 workflows are independently scheduled daily at 16:31 and 16:17 UTC. Their last stored scored snapshots are dated 2026-11-20. Daily scheduling does not establish completion for future dates.

## Distinguish historical datasets
- `ops/fwa_confirmatory.json`: 25 paired historical issue dates, 432 paired cases; uses Open-Meteo model archives and frozen earlier candidate comparisons. This is a separate model/source/protocol study and **must not be pooled** with native DINI GRIB prospective results.
- `ops/fwa_benchmark_history.json` (native v1): 7 observed entries, 3 paired temperature and 3 paired wind entries, from 2026-11-20T12:00Z. Only one issue day.
- `ops/fwa_geo_history_v2.json` (native geographic v2): 9 scored entries (5 temperature, 4 wind), one forecast run at 2026-11-20T15:00Z and one issue day.
- `ops/fwa_geo_dense_history_v1.json` (native geographic v2 under dense protocol): 36 scored entries, 20 temperature and 16 wind, four leads from **one originating forecast issue 2026-11-20T00:00Z**. Two validity dates, **one independent issue day**. Distinct lead times/stations do not create independent synoptic samples.
- The three native data products use different issue hours on the same 2026-11-20 issue date; they cannot be called three independent *days*, and each stream must retain its own identity.
- `ops/fwa_observed_regimes_fast_2026.json`: 33,259 observational rows across 234 days and 5 sites (2026-04-01 to 2026-11-20), 4,665 measured wind reports >=10 m/s, distributed over 173 calendar days with some station measured high wind. These are **not 33,259 paired forecasts**; correlated observations must not be interpreted as independent storms.

## Dense frozen v2 scores: descriptive only
- 20 temperature pairs: native HARMONIE MAE 1.17665 C, frozen FWA v2 1.26228 C (delta +0.08563 C, worse).
- 16 wind pairs: native HARMONIE MAE 1.33015 m/s, frozen FWA v2 1.29900 m/s (delta -0.03115 m/s, slightly better).
- 0 wind pairs with observed wind >=10 m/s, 0 forecast strong-wind cases. Thus **no prospective high-wind skill evidence yet**.
- 7 temperature cases with **model-defined** 2m–100m inversion conditions, spread across one issue day. There are 0 independently observed inversion-profile verifications; surface observations cannot establish actual atmospheric inversion.
- The predefined inferential gate is >=30 distinct independent issue dates and >=3 stations within an analyzed group; `ops/fwa_regime_readiness.json` reports 1 independent issue date. **29 additional independent issue dates** are required even for the overall date-count gate. High-wind and inversion subgroup adequacy require independent additional scrutiny; 30 overall dates will not automatically qualify every subgroup.
- Avoid reporting uncertainty intervals from a single model issue. Use paired corrections against unchanged native HARMONIE, cluster uncertainty by originating model issue day, and report site, observation source and lead separately.
- Be careful with IEM Vágar METAR timing/precision vs exact DMI station observations and missing Fugloy wind records; do not treat measurement systems as interchangeable.

## Next stage, without redoing finished work
1. Let the current scheduled workflows accumulate strictly predeclared native forecasts and matched observations, and monitor missing daily issues, failed leads, missing station readings, and archive reliability. Do **not** alter the frozen corrections in response to daily performance.
2. At each checkpoint, report counts of unique **model issue dates**, paired temperature/wind cases, distinct strong-wind dates, inversion-forecast issue dates, source/station coverage and missingness, not just number of rows.
3. Evaluate high-wind negative forecast errors and false negatives separately from mean MAE; make no claim about actual inversion verification absent multi-level observations.
4. After adequate independent issues and diverse regimes, estimate issue-clustered uncertainty; any proposed geographic candidate must be separately versioned and evaluated on genuinely unseen issues. Do not retrofit the current prospective dataset.
5. Do not misrepresent the historical Open-Meteo confirmatory scores as native-GRIB FWA v2 skill.

## Source-of-truth files
`ops/fwa_geo_dense_history_v1.json`, `ops/fwa_geo_dense_latest.json`, `ops/fwa_geo_history_v2.json`, `ops/fwa_benchmark_history.json`, `ops/fwa_regime_readiness.json`, `ops/fwa_observed_regimes_fast_2026.json`, `ops/fwa_confirmatory.json`, `ops/latest_success.json`, `docs/fwa_terrain_regime_study.md`.

This checkpoint is documentary; it does **not** certify future scheduled operations, additional forecast issues, operational superiority, or causality from geographic covariates.
