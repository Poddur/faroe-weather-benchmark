# First verified three-model comparison — 14 November 2026

## Independent WeatherNext source access: PROVEN
Source: [WeatherNext 3 direct-access run 43657936387](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43657936387) (SUCCESS, Python 3.12, no Google API credentials).

Archived result: [GitHub Release weathernext3-access-2026-11-14](https://github.com/Poddur/faroe-weather-benchmark/releases/tag/weathernext3-access-2026-11-14), six model values and manifest with SHA-256 `43d57d2ae0daf7a47b20a0c8eac9ec0222a56e8aa890de47f0bdca55bb5f31f8`.

- Third-party original dataset: [dynamical.org Google WeatherNext 3, 15-day 0.1° virtual](https://dynamical.org/catalog/google-weathernext3-forecast-15-day-0-1-degree-virtual/).
- Initialization: 2026-11-14 00:00 UTC. Lead +6 h, valid 06:00 UTC.
- Variables: 2m temperature in **degree Celsius** (dynamical already converted K to C), **10m scalar wind speed** in m/s, ensemble mean.
- Locations: Suður 06009, Tórshavn 06011, Eiði 06014. Selected cells: (61.4,-6.7), (62.0,-6.8), (62.3,-7.1) degrees. Longitude normalization 0–360 handled explicitly.
- Real DMI observation source: [run 43618246372](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43618246372), artifact 14122523629.
- Real IFS and DINI forecast source: [run 43648017660](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43648017660), artifact 14134832048.

## Strict matched UTC +6h comparison

All three models share **same initialization timestamp, valid timestamp, station and variable**; no interpolation of missing observations.

| Variable | ECMWF IFS MAE | HARMONIE DINI MAE | WeatherNext 3 MAE | Unit |
|---|---:|---:|---:|---|
| 2m temperature | 1.207 | 0.666 | 0.778 | °C |
| 10m scalar wind speed | 4.406 | 1.306 | 2.566 | m/s |

Each MAE uses **exactly three station values**, one single initialization and one lead time. This is not evidence of general model superiority. The operational IFS pilot is **0.25°**, compared to WN3 **0.1°** and high-resolution DINI, so resolutions also differ.

### WeatherNext 3 forecast values and observed values

| Station | WN3 temperature | DMI temperature | WN3 wind | DMI wind |
|---|---:|---:|---:|---:|
| Suður | 6.230 °C | 5.6 °C | 12.284 m/s | 13.6 m/s |
| Tórshavn | 5.020 °C | 3.6 °C | 13.344 m/s | 13.0 m/s |
| Eiði | 3.084 °C | 2.8 °C | 10.163 m/s | 16.2 m/s |

## Methodological limitations

1. Dataset download from a **historical archive on 15 Nov** does not establish actual prospective public publication on the 14 Nov issue, or preclude changes/backfill by the source. Verify model provenance for retrospective research.
2. No instrument-height or wind-period harmonization has been audited. Scalars are given as named by each dataset and should not be taken as identical effective observation definitions without review.
3. This is **one weather event (n=3)**, and it must not be used for a rank, significant difference or probabilistic reliability claim.
4. WeatherNext 3 individual ensemble members are not present in this dynamical 0.1° summary; the source provides mean and quantiles.
5. Historical archive availability extends to January 2026 via this third-party service, **not necessarily to 2024 or 2025**.
6. The normal dynamical.org JSON point API explicitly does not serve WeatherNext 3. Successful path is **dynamical-catalog > Icechunk/Zarr**.

## Operational state

WeatherNext historical read was demonstrated and saved, but **full 2026 backfill and scheduled WeatherNext real-time ingestion are not yet active**. Existing ECMWF/DINI/DMI operational workflows remain separate and unchanged.
