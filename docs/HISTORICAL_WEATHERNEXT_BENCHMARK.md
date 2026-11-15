# Historical WeatherNext 3 versus DMI — initial reproducible experiment

The first historical research workflow is located in [historical-weathernext-benchmark.yml](../.github/workflows/historical-weathernext-benchmark.yml). A push to that workflow automatically starts the pilot; it does not require the user to run a manual GitHub step.

## Experiment fixed before looking at errors

- Dates: **2026-10-01 00:00 UTC** and **2026-10-08 00:00 UTC**.
- Leads: +6, +12, +24 hours.
- Locations: DMI station IDs 06009 Suður, 06011 Tórshavn and 06014 Eiði.
- Parameters: 2m air temperature in Celsius, 10m scalar wind in m/s.
- Forecast source: global 0.1° Google WeatherNext 3 **historical archive** independently accessed through dynamical.org and Icechunk, summary statistic **ensemble mean**.
- Truth source: DMI original historical metObs station records.
- Exact key join: station_id + variable + valid_time. No interpolation; missing observations remain missing.
- Planned dataset: 2 initializations × 3 leads × 3 stations × 2 variables = **36 forecast rows**. The actual number of observation pairs may be smaller and must be reported.
- Each source raw DMI feature is preserved with SHA-256; WeatherNext sample CSV likewise.

## Outputs

When successful, GitHub Release `weathernext3-historical-pilot-2026-10` contains:
- `forecasts.csv`, `observations.csv` and `paired.csv`.
- `scores.csv`: n, MAE, RMSE, bias, independent initialization count by weather variable and lead.
- `coverage.csv`: all forecasts including missing-observation flags.
- `dmi_original_features.json`: complete original DMI response features returned by the pilot.
- `dmi_query_coverage.json`: observation counts for each station/parameter/date.
- `manifest.json`: experimental constraints, UTC dates, units, SHA-256 provenance and notes.
- `ops/weathernext_historical_pilot.json`: repository receipt populated only after the completed, successful collection.

## Research integrity

This is a **retrospective backtest**, not proof that a particular forecast was publicly obtainable at issue time, because the historical WeatherNext dataset may include after-the-fact backfilling. To claim prospective forecasting skill, establish model publication lineage and compare against same-period genuinely archived forecasts.

ECMWF/HARMONIE contemporaneous collection started in November 2026. That does **not** supply their October 2026 historical initialization cycles. The October pilot reports only WeatherNext-vs-DMI errors; it must not fabricate 3-model rankings.

Two independent dates are an initial technical pilot, not a valid general statistical comparison. Scale to systematic dates across winter/spring/summer/autumn only after checking historical coverage and DMI API stability; avoid post-hoc cherry-picking and data leakage.

WeatherNext database access via dynamical.org has already been independently verified for 2026-11-14T00Z using [successful GitHub run 43657936387](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43657936387). The new historical run is a separate, more extensive experiment.
