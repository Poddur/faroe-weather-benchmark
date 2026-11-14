# Matched forecast pilot — protocol

Created 2026-11-14. Run GitHub Actions workflow **Collect matching ECMWF + DINI issue (manual)**. It executes on GitHub-hosted Linux, no Windows.

## What constitutes an acceptable collection
- Pick **one issue time shared by both models**, an available HARMONIE 00/12 UTC issue at least 15 hours old and no more than 44 hours old.
- Query HARMONIE DINI by exact /instances/{issue}/position endpoint; never use the ambiguous /position latest-run shortcut for scientific evaluation.
- Fetch ECMWF IFS (preliminary 0.25-degree data) with same date/hour, 2m temperature and 10m wind components for +6h/+12h/+24h.
- Extract exactly 3 stations: 06009 Suður, 06011 Tórshavn, 06014 Eiði.
- Fail when HARMONIE nearest-grid distance exceeds 5km; reject missing fields, missing forecast leads and missing ECMWF GRIBs.
- Preserve **nine raw ECMWF GRIB files**, **three raw HARMONIE responses** and instance registry; hash files in manifest.
- Export 36 comparison-ready forecast rows (2 models × 3 sites × 3 leads × 2 variables) when complete.
- Model values are not verification scores. Actual DMI observations are collected separately *after* each forecast valid time has passed.

## Important limitations
- GitHub artifact retention is 14 days: **not permanent archiving**.
- 0.25-degree ECMWF is preliminary, not the final comparable 0.1-degree experiment.
- Temperature is modeled at 2m; observed sensor heights, local terrain representativeness and wind averaging periods require review.
- GitHub Actions is manually dispatched; no Scheduler or Cloud Run Job has been activated, and there is no billing change.
- The first manual run may expose schema or partial-availability issues; use its raw diagnostic archive to repair, not to claim success prematurely.

## Next verification stage
After this workflow succeeds:
1. Retain the artifact and check all raw-data hashes.
2. Obtain DMI observations for the exact valid timestamps (e.g., issue+6, issue+12, issue+24) once they have occurred.
3. Run a pairwise-only proof of concept with timestamp/unit matching, report sample size and caveats.
4. Set up persistent storage with restricted access, cost cap and retention controls.
5. When WeatherNext access is approved, add the third model using a verified identical issue/lead/observation intersection.

Research integrity rule: distinguish prediction values from observed values, prohibit look-ahead (do not fetch later reforecasts as if they were archived contemporaneous forecasts), and do not present single-day statistics as model skill.
