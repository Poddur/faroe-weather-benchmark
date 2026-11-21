# FWA terrain-conditioned weather regime study – pre-holdout assessment

## Evidence policy (frozen)
This study **does not** use the 2026-11-20+ prospective skill records for estimating corrections or threshold selection. The unchanged original HARMONIE forecast remains the primary control. Full prospective v1, geographic v2, winter and dense-snapshot series are separate.

## Development-only historical evidence
Source: original FWA pilot GitHub Actions run 44603911240, immutable `fwa-research-evidence` artifact; `forecasts.csv` and `observations.csv`, **only issue dates before 2026-08-20**.

Verified study: https://github.com/Poddur/faroe-weather-benchmark/actions/runs/44862396826
Machine-readable receipt: `ops/fwa_terrain_training_diagnostics.json`.

- 19 distinct forecast issue dates, 340 station/variable pairs (170 temperature, 170 wind) at 06009, 06011, 06014; +6, +12, +24 hours.
- Native baseline is historical HARMONIE DINI *via Open-Meteo*, not the newly collected original native GRIB, so do not directly merge numeric error estimates with the prospective native-GRIB scorecard.
- Observed wind >=10 m/s: 24 cases on 9 issue dates; HARMONIE mean signed error (forecast minus observation) -3.3125 m/s, MAE 3.3625 m/s.
- Observed wind <10 m/s: 146 cases; mean signed error +0.3534 m/s, MAE 1.4616 m/s.
- Exposed/raised TPI sites: Akraberg and Eiði, combined 114 wind cases, mean bias -0.5377 m/s; neutral-TPI Tórshavn 56 cases, mean bias +0.5964 m/s.
- Akraberg 57 wind cases, MAE 1.5298 m/s, bias -0.4246 m/s. Tórshavn 56, MAE 1.6964, bias +0.5964. Eiði 57, MAE 1.9632, bias -0.6509.
- Temperature signed biases vary strongly: Akraberg +0.7825°C; Tórshavn -0.0839°C; Eiði -0.8298°C. The two raised-TPI sites have **opposite temperature biases**: no evidence for a universal ridge temperature correction.

### Independent geographical covariates
Official Umhvørvisstovan shoreline *Strandalinja*, EPSG:5316. Provenance: `ops/fwa_official_shoreline.json` and `config/fwa_official_morphology_v2.json`.
Exact site-to-vector shoreline distances:
- Akraberg 92.66 m, raised-TPI
- Tórshavn 384.05 m, neutral-TPI
- Fugloy 70.80 m, lowered/hollow-TPI
- Eiði 663.27 m, raised-TPI
- Vágar EKVG 1622.49 m, lowered/hollow-TPI

The 100 m national coastline-distance layer is developed separately from the original 10 m DEM; unlike the old flat-zero indicator, its geometry is official shoreline. Topographic position index (TPI) is only a landscape form proxy, not definitive wind exposure, fjord channelling or aerodynamics.

## Verified full observed-weather census (2026-04-01 through 2026-11-20)
The fast batched DMI+METAR collection completed successfully at https://github.com/Poddur/faroe-weather-benchmark/actions/runs/44863268211 . Raw hourly DMI and native-time METAR records were preserved as a source-attributed gzip artifact, with coverage receipt `ops/fwa_observed_regimes_fast_2026.json`.
- **33,259 observational rows, 234 calendar days, five station sites.**
- **4,665 measured wind reports >=10 m/s across 173 unique calendar days at least one site** (multiple reports within storms/days are dependent).
- Akraberg: 5,527 rows, 1,520 high-wind reports, 143 days; maximum 30.7 m/s.
- Tórshavn: 5,543 rows, 560 high-wind reports, 88 days; maximum 24.8 m/s.
- Fugloy: 5,517 rows, 1,177 wind measurements, 218 high-wind reports, 37 days; maximum 17.3 m/s. Note incomplete wind availability.
- Eiði: 5,474 rows, 1,374 high-wind reports, 145 days; maximum 29.2 m/s.
- Vágar EKVG: 11,198 METAR rows, 993 high-wind reports, 90 days; maximum 21.09 m/s; reporting intervals generally 30 min, not hourly.
- Different strong-wind directions dominate at different sites: Akraberg SW, Eiði S, Vágar E/NW. This is *descriptive climatology* not a comparison of forecast skill.
- Surface-only observations **cannot verify an atmospheric temperature inversion**. The distinct native-model inversion cases must be evaluated prospectively with multi-level data.

## Four-lead prospective capture, verified
First successful fixed 00Z HARMONIE model-run batch: https://github.com/Poddur/faroe-weather-benchmark/actions/runs/44862554919 . All 6/12/18/24-hour lead cases collected.
- 20 matched temperature cases: original HARMONIE MAE 1.17665°C; frozen FWA 1.26228°C (worse).
- 16 matched wind cases: original HARMONIE MAE 1.33015 m/s; frozen FWA 1.29900 m/s (slightly better).
- Seven *unique station/valid-time modeled* temperature inversions, zero independent measured inversion verifications, no matched measured strong-wind events.
- These forecasts span **two valid dates but just one independent originating model issue**. Inferential cluster and readiness must be computed by forecast *issue day*, not valid day or individual lead. Updated evaluation: `src/fwa_dense_issue_audit.py` and `src/fwa_regime_readiness.py`.
- The physical correction must remain unchanged. No selection or tuning based on these prospective results.

## What can and cannot be inferred
**Observed**: higher error and material underforecasting for high-wind cases; signed baseline errors differ among locations. **Not established**: a causal link from coastline, valley/hollow or ridge category to the correction effect; prospective FWA improvements in high winds or inversions; transferability to an unseen station.

Only three historical training stations exist, two in the ridge proxy and one in the neutral proxy, so terrain-class effects are confounded with station identity. The development archive has no 2 m–100 m temperature inversion field. Atmospheric inversion diagnostics are forecast-defined and collected prospectively, **not measured observed inversions**.

## Pre-registered follow-up: not an outcome-selected model
1. Collect a 2026 observed-weather census at 06009/06011/06012/06014 and EKVG from DMI metObs and IEM METAR, preserving report times, 10 m wind uncertainty and distinct strong-wind days. Workflow: `fwa-observed-regimes.yml`; these **descriptive observations** are not a forecast skill evaluation by themselves.
2. Collect 4 fixed native HARMONIE lead times (6/12/18/24 hours) from each previous-day 00Z issue daily; no selection conditioned on storm forecasts or observed errors. Workflow: `fwa-dense-regimes.yml`; separate `ops/fwa_geo_dense_history_v1.json` when successful.
3. Stratify the same paired baseline-vs-FWA cases by (a) exact native-forecast wind sector, (b) forecast strong wind >=10 m/s, (c) observed strong wind >=10 m/s as a retrospective diagnostic only, (d) model 2 m/100 m inversion, (e) shoreline <=500 m / >500 m, and (f) TPI >=25m / <=-25m / neutral. Cross-tabulate by site; do not blindly pool different observing systems.
4. Before proposing *any* new candidate, report per-cell sample availability, 30 distinct valid-time dates minimum, physical data quality and station diversity. At least two independent stations per terrain regime are desired; our five sites do not yet achieve this for all crossed combinations.
5. Use earlier development-only dates to fit any new physics-regime parameters. Freeze a new algorithm ID and coefficients **before** a genuinely unseen subsequent period or new held-out locations. Never update frozen v2 or retroactively re-score its dates with a trained candidate.
6. Examine inversion-regime skill separately, with caution: native model inversion is a model forecast, not ground-truth verification of atmospheric inversion. Direct thermal profile observations are absent.
7. Assess high-wind false negatives and extreme underforecasting independently of MAE. The model must not improve average skill by hiding dangerous underpredictions.

## Governance
Original model forecasts and raw matched observations are immutable comparators. Source limitations or unavailable GRIB fields are reported, not imputed. No paid data access, no live redistribution or claims of operational meteorological superiority.
