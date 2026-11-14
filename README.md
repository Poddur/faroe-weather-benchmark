# Faroe Weather Benchmark

Reproducible comparison of **DMI station observations**, **ECMWF IFS**, **DMI HARMONIE**, and (when access is approved) **Google WeatherNext 3** for the Faroe Islands.

## Deployment status (2026-11-14)
- Repository established.
- Cloud deployment **NOT ACTIVE**; no jobs, bucket, schedule, or billing changes have been made.
- WeatherNext access is pending Google approval.
- Previous project archive: `Faroe_Weather_Benchmark_v0.3_CloudRun.zip`, provided in the ChatGPT conversation. The archive has **not yet been imported** into this repository.
- No real-weather accuracy results exist yet; never mistake synthetic examples for observations.

## Safety
Never commit API keys, service-account JSON, secrets, private station metadata, raw personal data, or downloaded GRIB archives. Before activating a schedule, confirm IAM, storage limits, costs, data coverage, and working live-source tests.

## Next steps
1. Import the contents of the v0.3 ZIP to the **root** of this repository (not in an extra nested folder).
2. Confirm quality and source settings with `pytest -q`.
3. Validate actual DMI stations, and create `data/stations_verified.csv` (do not use demonstration coordinates).
4. Review `deploy/DEPLOY_GOOGLE_CLOUD_DA.md` from the archive.
5. Validate Cloud Run Job manually **before** enabling Cloud Scheduler.
6. Add WeatherNext only after access approval and schema verification.

A separate weather deployment must never modify `sementicx-worker` or the Proof Layer repository.
