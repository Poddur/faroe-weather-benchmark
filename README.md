# Faroe Weather Benchmark

Reproducible comparison of **DMI observations**, **ECMWF IFS**, **DMI HARMONIE**, and — once approved — **Google WeatherNext 3** for the Faroe Islands.

## Current status — 14 November 2026
- Python modules for paired forecast evaluation, station discovery, DMI observation collection, ECMWF IFS collection, HARMONIE collection, per-run archiving, and Cloud Run entrypoint are in this repository.
- GitHub Actions runs unit tests on pushes and pull requests; **a successful hosted run has not yet been independently verified**.
- **Cloud Run is NOT deployed.** No scheduler, cloud bucket, service account, or billing change has been created.
- **No real forecast accuracy results exist yet**. Any demonstration data is synthetic.
- Google WeatherNext 3 access is **pending**; the BigQuery adapter from the earlier v0.4 ZIP has not been imported or live-verified.
- DMI station IDs, instruments and observation coverage must be validated before collection can run.

## Safe first checks
```bash
python -m pip install -r requirements.txt
python -m pytest -q
python src/discover_dmi_stations.py --output data/stations_candidates.csv
```
Inspect candidates against DMI metadata and build `data/stations_verified.csv` yourself only from verified data; never automatically promote candidates.

## Intended cloud environment
Use a **new** Cloud Run Job and dedicated Cloud Storage bucket in an explicitly verified GCP project. Do not modify existing `sementicx-worker` or Proof Layer services. Ensure dedicated least-privilege IAM, budget alerts, manual one-off test, archive validation and retries before enabling Cloud Scheduler.

The Dockerfile requires a verified stations file mounted or provided at runtime, and valid `WEATHER_ARCHIVE_BUCKET` / `WEATHER_STATIONS` settings. Without those, it deliberately exits rather than reporting fake success.

## Model comparison rules
Same stations, variables, physical units, UTC initialization and valid times, and common verification sample for all models. The benchmark reports MAE, RMSE, bias, and paired MAE differences with day-block bootstrap uncertainty. HARMONIE availability, actual API schemas, sensor heights, and GRIB parsing still require live tests.

## Security
The repository is currently **Public** (last checked during this session). Never commit secrets, credentials, sensitive configuration, GRIB archives or private data. Change repository visibility to Private in GitHub Settings if desired.
