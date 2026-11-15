# Alternative WeatherNext 3 historical access — direct Icechunk test

Independent third-party source: https://dynamical.org/catalog/google-weathernext3-forecast-15-day-0-1-degree-virtual/

## Source and scope
- Historical global 0.1-degree WeatherNext 3 ensemble summary forecasts with initialization cycles from **2026-01-01 UTC** onward.
- Catalog uses 0..360 longitude, dimension names init_time, lead_time, statistic, y, x. Temperatures are **already in Celsius**, winds **m/s**; never subtract 273.15 again.
- The catalog's historical data uses CC BY 4.0, with Google/dynamical.org attribution and third-party restrictions noted on the product page.
- **The general dynamical.org point API explicitly does not support WeatherNext 3 as of 2026-11-15.** The supported independent route is public Icechunk/Zarr (STAC HTTPS, HttpAccess) or dynamical-catalog.
- Because spatial chunks span the entire global grid (one init/lead/statistic slice), *a single point may require a sizable source read.* Restrict this pilot to a single initialization, 6-hour lead, 2 variables and three locations.

## Explicit test case
- Initialization: 2026-11-14 00:00 UTC.
- Forecast valid time: 2026-11-14 06:00 UTC.
- Statistic: ensemble mean.
- Temperature (C), 10m scalar wind speed (m/s) at DMI sites Suður 06009, Tórshavn 06011 and Eiði 06014.
- Source artifact: `outputs/weathernext-direct-test/forecasts.csv`, SHA in `manifest.json`.
- GitHub workflow: [WeatherNext independent historical access test](../.github/workflows/weathernext-dynamical-test.yml). Only the test run is triggered by workflow changes; this does not alter the existing real-time collection.
- On success, a reproducibility ZIP is uploaded to GitHub Release `weathernext3-access-2026-11-14`, along with a machine-readable receipt `ops/weathernext_access.json`.

## Important data integrity caveats
1. Historical presence **does not establish that the forecasts were available at the issue timestamp in real time**. Verify source publication and model version to guard against retrospective backfilling.
2. Three stations from one historical initialization are only a connectivity proof, not an accuracy conclusion.
3. 2026 historical retrieval does not automatically establish 2024–2025 data availability from this mirror.
4. Primary 0.1-degree temperature is different from 0.05-degree station-trained head; do not merge them.
5. WeatherNext summary wind speed is an ensemble mean of wind speed, not necessarily the magnitude of mean u/v vectors. Define comparable statistics accordingly.

## Notes from first GitHub run
- First triggered test run: [43657876068](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43657876068). It failed **at dependency installation**: Python 3.11 unsupported by dynamical-catalog >=1.0.0. No network data fetch attempted.
- Fixed GitHub test runtime to **Python 3.12** and triggered another run.
