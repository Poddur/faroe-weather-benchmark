# FWA geographic extension v2: first verified run

## Identity and provenance
- Independent run: https://github.com/Poddur/faroe-weather-benchmark/actions/runs/44861806254
- Frozen version: `fixed_native_boundary_v2_new_sites`. Original HARMONIE DINI native values remain the baseline on exactly the same station/forecast-validity pairs.
- First processed forecast: HARMONIE run `2026-11-20T15:00:00Z`, valid `2026-11-20T21:00:00Z`, six-hour lead.
- DMI metObs stations: 06009 Akraberg, 06011 Tórshavn, 06012 Fugloy, 06014 Eiði.
- Airport station: EKVG Vágar, Iowa Environmental Mesonet METAR, last report at 20:50Z (10 minutes **before** valid time); no future observation is allowed.
- Original terrain is the supplied Umhvørvisstovan `FO_DTM_2009_10m.tif`. Fugloy and Vágar profiles use nearest 100 m derived terrain cell (respectively 41.9 m and 8.7 m centre offset), 72 sectors and a 2 km radius; station metadata heights are 54 m and 85 m.
- The new sites use **approximate** sector profiles and have not been separately validated as the correct local 10 m wind exposure. Fugloy registered height (54 m) differs by 12.7 m from the nearest raster cell (66.7 m), a measurement-site uncertainty.

## Results – initial independent snapshot only
| Variable | Matched station observations | Native HARMONIE MAE | FWA v2 MAE | Change, corrected minus baseline |
|---|---:|---:|---:|---:|
| Temperature | 5 | 0.86285 °C | 0.98386 °C | **+0.12102 °C (worse)** |
| Wind speed | 4 | 1.13760 m/s | 1.19130 m/s | **+0.05370 m/s (worse)** |

Only one distinct valid date has been evaluated; these figures establish neither superiority nor inferiority in general. The 95% uncertainty calculation is correctly unavailable until sufficient dates and stations exist.

### New-site results
- Fugloy (06012) temperature absolute error: HARMONIE 1.19016 °C; FWA 1.48360 °C. No matched Fugloy wind reading in this valid-time sample.
- Vágar (EKVG) temperature: HARMONIE 1.51121 °C; FWA 2.10186 °C. Wind: HARMONIE 1.56714 m/s; FWA 1.42413 m/s.
- Vágar METAR observations are not identical in precision, instrumental conditions or reported time to exact-hour DMI observations; keep source/station-specific scores visible and do **not** combine without corresponding caveats.

## Stratification registered
- By native model wind direction: 8 pre-defined compass sectors. On the first date, only N and NE were present.
- By high wind: forecast 10 m wind >=10 m/s. None of these first observations was strong-wind forecast; evidence absent, not "pass".
- By native 2m-100m inversion: native `t100 > t2`, fixed before outcome evaluation. The one inversion case was EKVG; FWA temperature performance was worse there.
- Pre-registered sample eligibility for inference: minimum 30 distinct dates and 3 stations; date-cluster bootstrap of paired absolute errors.
- All v1 results and winter experiment remain unchanged. V2 results are kept separately in `ops/fwa_geo_history_v2.json`.

## Prospective plan / scientific limitations
- Continue the daily scheduled geographic extension without retuning coefficients on the observed first-day errors.
- Follow the unadjusted original HARMONIE control, per-station deltas, all matched observations and missingness.
- More observations under different wind directions, >10 m/s events, and inversions are essential before selecting a replacement candidate.
- Never interpret a forecast-derived inversion as independent observed confirmation of inversion. Validate atmospheric stability separately if direct vertical observations become available.
- For actual strong-wind reliability, report observed and forecast-defined regimes separately once enough observations exist.
