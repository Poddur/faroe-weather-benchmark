# Historical WeatherNext 3 validation, Faroe Islands — January–October 2026

**Study completed and source-verified:** 15 November 2026.

## Executive summary

The seasonal, **predeclared 20-initialization** retrospective WeatherNext 3 study completed successfully. We retrieved **360 historical forecasts** for three Faroe Islands DMI weather stations, with lead times +6, +12, +24 h and two variables (2m air temperature and 10m wind speed). **352 of 360** values (97.8%) matched real hourly observations from DMI.

Across all lead horizons, the descriptive mean absolute error was:

- **2m temperature: 0.879 °C** (N=176, RMSE 1.151 °C, bias +0.481 °C).
- **10m wind: 2.394 m/s** (N=176, RMSE 3.174 m/s, bias −0.554 m/s).

These are direct historical WeatherNext-vs-DMI observations, **not** evidence that WeatherNext 3 beats ECMWF or HARMONIE. Neither of those models has a comparable January–October 2026 historical issue archive currently in this project.

## Reproducible proof

- [Source collection GitHub Actions run 43664002490](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43664002490): **success**, including unit tests, data retrieval, release archiving and provenance receipt.
- [Independent science report run 43665093959](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43665093959): **success**, including hash re-verification and cluster bootstrap analysis.
- [Immutable source research archive and separate scorecard](https://github.com/Poddur/faroe-weather-benchmark/releases/tag/weathernext3-seasonal-2026). Assets: `weathernext3-seasonal-2026.zip` and `weathernext3-2026-research-scorecard.zip`.
- [Machine-readable source run receipt](../ops/weathernext_seasonal_2026.json); [independent report receipt](../ops/weathernext_seasonal_scorecard.json).

The original archived files were inspected independently: **all three SHA-256 checks passed**, on `forecasts.csv`, `observations.csv` and `dmi_original_features.json`.

## Sampling plan, fixed before error analysis

20 initialization dates: the 1st and 15th of every month from **January through October 2026**, all at 00:00 UTC.

DMI stations:
- **06009 Suður**
- **06011 Tórshavn**
- **06014 Eiði**

WeatherNext 3: Google 0.1-degree 15-day virtual product via dynamical.org and public Icechunk/Zarr, ensemble **mean**. Source temperature in Celsius, scalar wind speed in m/s. Verification: real DMI metObs station observations at the *exact valid timestamp*. No missing values imputed or interpolation performed.

## Observed errors by lead time

MAE, RMSE, signed bias and 95% *issue-level cluster bootstrap* intervals. The intervals reflect only sampling variability over the selected initialization dates, not systematic model or observation uncertainty.

| Variable | Lead | Matched N | Independent issues | MAE | RMSE | Bias | Bootstrap 95% MAE interval |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2m temperature (°C) | +6h | 57 | 19 | 0.716 | 0.932 | +0.425 | [0.558, 0.910] |
| 2m temperature (°C) | +12h | 60 | 20 | 0.979 | 1.276 | +0.330 | [0.737, 1.287] |
| 2m temperature (°C) | +24h | 59 | 20 | 0.935 | 1.207 | +0.688 | [0.688, 1.203] |
| 10m wind speed (m/s) | +6h | 57 | 19 | 2.080 | 2.906 | −0.531 | [1.479, 2.742] |
| 10m wind speed (m/s) | +12h | 60 | 20 | 2.532 | 3.337 | −0.738 | [1.928, 3.215] |
| 10m wind speed (m/s) | +24h | 59 | 20 | 2.557 | 3.253 | −0.389 | [2.104, 3.057] |

**Interpretation:** In this deliberately sparse 20-date sample, average temperature and wind errors are lower at +6h than at +12h and +24h. This does not prove a monotonic lead-time law or general seasonal skill.

## Station differences

MAE over all three lead times and 20 issue dates (N differs because of missing observations):

| DMI station | Matched N / variable | Temperature MAE (°C) | Wind MAE (m/s) |
|---|---:|---:|---:|
| Suður (06009) | 59 | 0.960 | 1.920 |
| Tórshavn (06011) | 58 | 0.896 | 1.844 |
| Eiði (06014) | 59 | 0.781 | 3.408 |

Eiði's wind discrepancy is markedly larger in this sample. Do **not** infer that the model is locally inferior until sensor height, exposure, wind averaging convention, terrain, and DMI QC are checked.

## Month-by-month descriptive MAE

| Month 2026 | Temperature MAE °C | Wind MAE m/s |
|---|---:|---:|
| January | 1.573 | 2.558 |
| February | 0.772 | 2.868 |
| March | 0.513 | 3.014 |
| April | 0.959 | 2.860 |
| May | 0.580 | 1.986 |
| June | 0.680 | 1.297 |
| July | 1.530 | 1.330 |
| August | 0.780 | 1.534 |
| September | 0.839 | 2.135 |
| October | 0.668 | 4.320 |

Only **two chosen initializations per month** were inspected (one on the 1st and one on the 15th), so these are *sample-specific monthly summaries*, NOT official monthly model verification scores.

## Limits of the scientific conclusion

1. The data are a **retrospective archive**, not a contemporaneously preserved operational feed. We have not established WeatherNext 3 model-publication provenance or whether any archive backfill happened.
2. We do **not** possess matching ECMWF IFS and HARMONIE forecast initializations for January–October 2026. A claim that WeatherNext is better/worse than those models on these dates is therefore unjustified.
3. Sample size = **20 forecast issues**, NOT 352 independent weather events. Stations in the same weather system and forecast horizons are correlated.
4. 20 dates across ten months provide a helpful historical sample but not daily, storm-stratified or climate-representative analysis.
5. **Eight** forecast values had no same-valid-time DMI observation. These were excluded openly.
6. Wind observation height/averaging and terrain representativeness require field metadata verification; instruments may not measure precisely the model's nominal 10m wind.
7. The reported percentile intervals are naive issue-level nonparametric bootstrap intervals; they **do not** cover source bias, selection effects, long-term regime shifts, or all clustered dependencies.

## Conclusion

**Access and retrospective verification are technically solved** for this 20-date WeatherNext 3 experiment. The archived files are reproducible, scorecards are validated, and analysis is descriptive with clear limitations. This is meaningful progress toward a benchmark; **no scientifically defensible three-model superiority ranking exists yet** for the historical period.

Source/code archive: `Poddur/faroe-weather-benchmark`.
