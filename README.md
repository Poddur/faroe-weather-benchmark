# Faroe Weather Benchmark

## Verified retrospective WeatherNext 3 study (15 November 2026)

**Complete seasonal sample:** 20 predeclared initialization dates across January–October 2026, **360 historical WeatherNext 3 forecasts**, **352 paired DMI station observations**, and independent SHA-validated research scorecard. Descriptive pooled MAE: **0.879 °C** (temperature) and **2.394 m/s** (wind). This is retrospective WeatherNext-vs-DMI evaluation only; matched ECMWF/HARMONIE historical forecast cycles have not been acquired for the period.

- [Full historical research report](docs/WEATHERNEXT_2026_HISTORICAL_FINAL_REPORT.md)
- [Audited GitHub Release archive + scorecards](https://github.com/Poddur/faroe-weather-benchmark/releases/tag/weathernext3-seasonal-2026)
- [Verified historical collection run](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43664002490)
- [Independently verified scorecard generation](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43665093959)


Research-grade, reproducible **Faroese station verification** for ECMWF IFS, DMI HARMONIE DINI, DMI metObs, and future Google WeatherNext 3.

## Current operational architecture (14 November 2026)

**GitHub Actions automation has been configured** in [.github/workflows/operational-archive.yml](.github/workflows/operational-archive.yml):

- Scheduled **04:27 and 22:27 UTC** daily, plus manual dispatch.
- Collect one *identical issue time* for ECMWF IFS (0.25-degree pilot) and HARMONIE DINI, with +6/+12/+24 h forecasts at Suður, Tórshavn and Eiði.
- Download 90 hours of overlapping actual DMI observation measurements, and preserve raw JSON and original ECMWF GRIB2.
- Validate source SHA-256 hashes, missing model counterparts and duplicate observations.
- Upload an audit copy to Actions artifacts (30-day retention).
- Upload a bounded (~under 30 MB) per-issue ZIP to a **weekly GitHub Release** (does not have the Actions artifact expiry; remains available while repository/releases are maintained).
- Record latest successful archive at [ops/latest_success.json](ops/latest_success.json) **once the first run succeeds**.
- Open or update one GitHub issue on automated collection failure.

**Weekly verification**: [.github/workflows/weekly-verification.yml](.github/workflows/weekly-verification.yml), Sundays 08:43 UTC. Downloads recent weather-data releases; verifies source hashes; deduplicates *identical* overlapping measurements, refuses conflicting records; calculates paired MAE/RMSE/bias against DMI observations; marks findings from fewer than ten independent issue dates as exploratory. Publishes the report to the weekly GitHub Release and Actions artifacts.

### Verification status

The prior **manual matched collection successfully produced 36 forecast records** and raw evidence from ECMWF + DINI. The actual first automatic scheduled/release-publishing collection **has not yet been independently confirmed**. Do not confuse committing a workflow with proof that it ran.

No Google Cloud Run Job, Scheduler, GCS bucket or Google billing change has been created by the assistant. Cloud Run requires separate Google Cloud administration permissions and is not required for the GitHub-based pilot.

WeatherNext 3 access is still pending Google approval. Its schema/access cannot be verified before approval.

### Key constraints

- Research pilot includes 0.25-degree ECMWF IFS, not the future preferred 0.1-degree IFS product.
- Sensor heights and wind averaging definitions need confirmation before formal claims.
- GitHub scheduled jobs may be delayed/dropped and may be automatically disabled after 60 days without repository activity on public repositories.
- GitHub Release assets are a pragmatic long-lived research archive, not an independently managed offsite backup or contractual long-term storage SLA.
- Repository is **Public** as last checked. Weather station data are nonpersonal public-source data; never commit API credentials or sensitive files.
- Check repository storage, GitHub Actions minutes and release growth regularly. Once a Google Cloud Storage bucket can be provisioned, move raw-file archives there with retention and spending controls.

### Primary historical evidence

- [DMI pilot observations](docs/DMI_OBSERVATION_PROBE_2026-11-14.md)
- [First paired forecast/observation measurements](docs/FIRST_PAIRED_OBSERVED_ERRORS_2026-11-14.md)
- [Verified first matching model-run source files](docs/FORECAST_LIVE_RESULTS_2026-11-14.md)
- [Protocol](docs/MATCHED_FORECAST_PILOT.md)

### How to audit operations

- [GitHub Actions](https://github.com/Poddur/faroe-weather-benchmark/actions)
- [Persistent Research Releases](https://github.com/Poddur/faroe-weather-benchmark/releases)
- [Latest successful archival heartbeat](ops/latest_success.json) (created automatically when first successful run completes)
- [Weekly report workflow](.github/workflows/weekly-verification.yml)

**Do not use synthetic samples as actual results. Do not claim superiority without independent longitudinal verification.**
