# FWA Atmospheric prospective benchmark protocol (frozen candidate v1)

## Goal
Test whether terrain-informed, physically bounded corrections to **native** HARMONIE DINI improve forecasts for actual Faroe Islands weather stations. This is an experiment, not an operational public forecast service.

## Forecast collection
- Daily scheduled run: 16:17 UTC, GitHub Actions workflow `.github/workflows/fwa-prospective.yml`.
- Retrieve an **already completed** native HARMONIE DINI surface-field forecast from DMI Open Data. The current regional extractor chooses a run approximately 12 hours old and a +6-hour valid time.
- Preserve the original model-run and valid-time identity, regional native GRIB SHA-256, units, wind-coordinate rotation controls and extraction QA.
- Pair only actual DMI observations that match exact UTC validity and station IDs. Do not infer missing observations.
- Do not include any observations in the correction algorithm. They may enter scoring only after predictions are fixed.
- Store new paired scores in `ops/fwa_benchmark_history.json`, idempotently keyed by run, validity, station and parameter; reject conflicts. Latest run metadata: `ops/fwa_benchmark_latest.json`.
- All raw-source data access obeys DMI/Open Data licensing and source attribution. Do not publish forecasts before validity or claim DMI endorsement.

## Frozen v1 model
Implemented in `src/fwa_prospective_benchmark.py`, version `fixed_native_boundary_v1`. Original HARMONIE predictions are the same-grid baseline.

- Temperature: native 2 m temperature corrected using the native 2-100 m lapse rate (bounded -10 to +12 K/km), local recorded terrain height and native GRIB surface geopotential height. Correction clipped to ±2°C. This is a *prototype approximation*, not a full thermodynamic downscaling solution.
- Wind: native true-east/north 10 m vector speed, directional 100 m wind and the station-specific **precomputed** 2 km shelter angle. Fixed multiplicative shelter parameter 0.15; correction bounded to 0.75-1.25.
- This candidate does **not** calculate a moist Froude number or resolve flow around fjords. It does **not** use observations to choose its daily parameters. The station geometry and exposure-profile provenance need continued auditing.
- Initial direct scores are restricted to stations with verified terrain profile and coordinate identity (06009, 06011, 06014). 06012 is retained as baseline-only until independently verified station terrain is incorporated. Vágar METAR is not compared at exact hour without an explicit pre-registered temporal matching policy.
- The all-island 146,067-cell terrain engine remains a separate prototype; this prospective benchmark validates point forecasts, not the national grid's spatial accuracy.

## Evaluation
- MAE per parameter: both original and corrected predictions scored on **identical station/time pairs**. Never compare disjoint samples.
- Do not claim statistically demonstrated improvement until at least 30 distinct forecast-valid dates and three stations have paired data for a variable.
- After eligibility, report paired (corrected minus raw) MAE 95% date-cluster bootstrap interval, pooled and broken down by station, weather regime and lead time if sample sizes permit.
- Record availability and excluded observations; do not cherry-pick dates, wind directions or stations.
- Treat strong winds and coastal sites as independent safety/reliability checks. A mean-MAE improvement alone is insufficient for deploying public forecasts.
- Existing rolling three-model benchmark compares ECMWF, HARMONIE and WeatherNext 3 under separate archival conditions. Do not silently combine results from distinct runs/leads.
- Any subsequent parameter tuning or station-coverage extension becomes a **new separately versioned candidate**, evaluated only on fresh dates or a distinct holdout. Preserve v1 as benchmark.

## Deployment gate
Do **not** describe FWA as the best weather model for the Faroe Islands merely because one or a few dates have lower error. Demonstrate stable geographic and time-independent gains across seasons, wind regimes, all relevant variables and reliable 10 m sensor comparisons.
