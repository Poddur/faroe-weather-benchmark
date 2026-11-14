# Operational acceptance — 14 November 2026

## End-to-end verification (real external source data)

**Automated collection:** [GitHub Actions run 43649549940](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43649549940), status **success**.

All mandatory stages succeeded: 14+ Python tests, common ECMWF/DINI model issue collection, DMI observation collection, SHA-256 and pairing verification, bounded ZIP creation, GitHub Release publication and success heartbeat.

- Model initialization time: **2026-11-14 00:00 UTC**.
- Forecast rows: **36** (ECMWF IFS 0.25°, HARMONIE DINI, three Faroese sites, +6/+12/+24h, 2 variables).
- DMI observation rows: **500** (temperature and 10m wind, 90-hour overlapping window).
- GitHub release tag: [weather-data-2026-W46](https://github.com/Poddur/faroe-weather-benchmark/releases/tag/weather-data-2026-W46).
- Persistent operational receipt: [ops/latest_success.json](../ops/latest_success.json).
- Short-term audit artifact: GitHub Actions ID **14135298070**, expires 2026-12-14.

**Initial run failure:** [43649196446](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43649196446) raised DMI HTTP 429. Both DMI adapters now implement 2.5-second pacing and bounded Retry-After-aware exponential backoff. The incident was tracked in GitHub issue [#1](https://github.com/Poddur/faroe-weather-benchmark/issues/1) and closed following successful verification.

## Weekly analysis acceptance

**Real automated weekly test:** [GitHub Actions run 43649702642](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43649702642), status **success**.

- 2 valid ZIP archives, 0 invalid.
- After de-duplication: **36 distinct forecast rows**, **652 distinct observation rows**.
- Matched observation/forecast rows: **24**, all in the 00 UTC 14-Nov issue, +6h/+12h.
- Independent model issue days: **1**.
- Scientific interpretation: **exploratory only**. The system explicitly warns there is not enough independent data to determine a superior model.
- Weekly result receipt: [ops/latest_weekly_analysis.json](../ops/latest_weekly_analysis.json).
- Weekly report artifact ID **14135068578**; report also published to the weekly release.

## Scheduling and storage

- Operational collection: daily at **04:27 and 22:27 UTC** by GitHub Actions. Manual trigger available.
- Verification: Sundays **08:43 UTC**.
- Operational ZIPs stored in **GitHub Releases** without the 30-day Actions-artifact expiration; archive longevity depends on retaining the repository and its assets, not a guaranteed storage SLA.
- On collection failure, an issue is automatically opened or updated. External provider outages/rate limits can still cause individual failed cycles.
- The system is **not** deployed on Cloud Run or Google Cloud Storage; there is no GCP administration connector in this chat.
- WeatherNext 3 connector has been coded from Google's published BigQuery schema but **not activated**: Google dataset approval and explicit credentialed access are pending.
- ECMWF IFS remains on the verified 0.25° operational pilot grid. A 0.1° high-resolution experiment has not yet been accepted for cost/bandwidth/storage.

## Remaining research conditions

Sensor height, wind averaging period, observation QC and seasonal performance must be verified prior to scientific claims. Only one independent issue day has been measured so far. **No model is declared best.**
