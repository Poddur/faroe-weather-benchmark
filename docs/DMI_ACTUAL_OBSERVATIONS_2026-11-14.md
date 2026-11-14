# DMI actual observation pilot — 2026-11-14

**Provenance:** GitHub Actions run [43618246372](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43618246372), job 132517943667. Completed successfully. Original downloadable artifact `dmi-pilot-hourly-observations` (artifact ID 14122523629; expires 2026-11-28). GitHub ZIP digest `sha256:59ab47a492dbfc5f1ca8eaf32f7ad3428a2cd7c7cb209926d177c85bd6328d78`.

Run window inclusive: **2026-11-13 15:00 UTC through 2026-11-14 16:00 UTC** (26 possible hourly timestamps). All values in `dmi_observations_hourly.csv` are actual DMI responses, **not** model predictions or synthetic data. Raw source `dmi_observations_hourly.raw.json` has **1,420 original DMI records**; exactly **304 hourly aligned records** are in the normalized CSV (non-hourly times excluded).

| station | variable | hourly n | min | max | mean | unit |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 06009 Suður | temperature_2m | 26 | 2.6 | 8.1 | 5.84 | °C |
| 06009 Suður | wind_speed_10m | 26 | 5.9 | 17.7 | 13.68 | m/s |
| 06009 Suður | msl_pressure | 26 | 991.2 | 999.3 | 994.78 | hPa |
| 06009 Suður | precipitation_1h | 26 | 0.0 | 0.0 | 0.00 | mm |
| 06011 Tórshavn | temperature_2m | 26 | 1.7 | 7.5 | 4.72 | °C |
| 06011 Tórshavn | wind_speed_10m | 26 | 6.5 | 16.3 | 12.40 | m/s |
| 06011 Tórshavn | msl_pressure | 26 | 988.6 | 997.2 | 992.56 | hPa |
| 06011 Tórshavn | precipitation_1h | 26 | 0.0 | 2.0 | 0.50 | mm |
| 06014 Eiði | temperature_2m | 24 | 1.0 | 6.2 | 3.71 | °C |
| 06014 Eiði | wind_speed_10m | 24 | 9.7 | 16.2 | 12.88 | m/s |
| 06014 Eiði | msl_pressure | 24 | 987.4 | 997.2 | 992.59 | hPa |
| 06014 Eiði | precipitation_1h | 24 | 0.0 | 1.4 | 0.50 | mm |

Hourly slot gaps for station 06014 across all four variables: **2026-11-13 20:00 UTC** and **2026-11-14 05:00 UTC**. 06009 and 06011 have no missing top-of-hour slots in this window.

No duplicate (station, variable, valid_time) rows in normalized CSV. Units are assigned in the adapter; **source metadata did not explicitly include per-measurement units**, so independent unit verification is still required. The sampled raw DMI `properties` fields were `parameterId`, `created`, `value`, `observed`, `stationId`, not an explicit QC flag. Thus *successful API response and lack of duplicate timestamps are not sufficient to certify meteorological quality*.

### Next scientific gates
1. Preserve downloadable artifact beyond 14-day retention in controlled object storage; do not publish raw data as a code commit.
2. Verify DMI parameter definitions, measurement height/representativeness, station validity intervals and sampling protocol.
3. Validate real ECMWF IFS run/GRIB schema and HARMONIE domain and EDR schema; record init_time separately from valid_time.
4. Do a matched-time, matched-variable benchmark and report paired sample size and uncertainty, not unpaired point estimates.
5. WeatherNext 3 requires separate access approval.
