# WeatherNext 3 retrospective evidence: 1 and 8 October 2026

Status: **Completed, audited source dataset. Exploratory research only.**

- Successful job: [43659008036](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43659008036).
- Raw source and tabular data: [GitHub Release weathernext3-historical-pilot-2026-10](https://github.com/Poddur/faroe-weather-benchmark/releases/tag/weathernext3-historical-pilot-2026-10).
- Machine receipt: [ops/weathernext_historical_pilot.json](../ops/weathernext_historical_pilot.json).
- Dates: 2026-10-01 and 2026-10-08 at 00 UTC; horizons +6, +12 and +24 hours; three stations (Suður, Tórshavn, Eiði); 2 variables (2m Celsius temperature, 10m wind speed m/s).
- Forecast values: **36**, DMI station observations **36**, matched samples **36/36**.
- Source provenance hashes in manifest: forecast CSV `ee9a05fa0516c2e4a0b170511cd9c78108645afde7d62933baba938e045b41c5`, observations `c394e32bbd02a32ba8d1ae6dcdd9aa40af8be6bdb34526c20add031f8a206481`, original DMI API features `72fa11275eca270e825ecd8af2ac4deae08b801fef9d3f8fac7db7fb8995813f`.

## Exact historical WeatherNext 3 error metrics

| Variable | Horizon | N station values | MAE | RMSE | Signed bias |
|---|---:|---:|---:|---:|---:|
| 2m temperature | +6h | 6 | 0.794 °C | 0.885 °C | +0.338 °C |
| 2m temperature | +12h | 6 | 0.700 °C | 0.903 °C | +0.128 °C |
| 2m temperature | +24h | 6 | 0.378 °C | 0.545 °C | +0.215 °C |
| 10m wind speed | +6h | 6 | 3.418 m/s | 4.779 m/s | −0.696 m/s |
| 10m wind speed | +12h | 6 | 3.931 m/s | 4.681 m/s | −1.440 m/s |
| 10m wind speed | +24h | 6 | 4.017 m/s | 4.614 m/s | −1.162 m/s |

Across leads (pooling N=18 station/valid-time values for each variable): temperature MAE **0.624 °C**, RMSE **0.795 °C**, bias **+0.227 °C**; wind MAE **3.789 m/s**, RMSE **4.691 m/s**, bias **−1.100 m/s**. Pooled-lead metrics are only descriptive.

## Critical distinction

The two initialization dates are the only **independent forecast issues** in this pilot. Treating 36 station values as 36 independent episodes exaggerates statistical strength. We therefore do not compute a superiority p-value, infer a seasonal generalization, or rank WeatherNext against other models from this sample.

WeatherNext is a **retrospective archive**, whose original contemporaneous publication and potential model backfilling have not been verified. DMI sensors, wind averaging periods and instrument exposures still require validation.

## Registered expansion

The repo now contains a 20-date, January–October 2026, predeclared seasonal extension, comparing WeatherNext against original DMI observations. Its completion must be verified separately through `ops/weathernext_seasonal_2026.json` and the release `weathernext3-seasonal-2026`. No seasonal results are claimed here until that receipt is available.
