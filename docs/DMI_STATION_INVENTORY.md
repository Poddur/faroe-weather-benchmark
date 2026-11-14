# DMI Faroe Islands station inventory — provenance checked 2026-11-14

Source: GitHub Actions run [43616097824](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43616097824), artifact `dmi-faroe-station-candidates` (ID 14121747746). Metadata from DMI `metObs/collections/station/items`. The original artifact expires on 2026-11-28.

**This is not a set of approved benchmark stations.** Station status is metadata only; observation completeness and instrument heights remain unknown. All anemometerHeight values in this returned metadata are null.

| ID | Latest record name | lat | lon | stationHeight m | metadata versions | Since (earliest metadata) | Current validFrom |
|---|---|---:|---:|---:|---:|---|---|
| 06007 | Nolsoy | 61.9580 | -6.6170 | 94.5 | 1 | 2022-05-25 | 2022-05-25 |
| 06008 | Frodba Heliport | 61.5437 | -6.7745 | 23.47 | 3 | 2009-05-18 | 2024-11-22 |
| 06009 | Sudur | 61.3957 | -6.6818 | 89.6 | 3 | 1996-03-20 | 2024-06-14 |
| 06011 | Torshavn | 62.0231 | -6.7647 | 54.0 | 5 | 1967-03-19 | 2025-04-23 |
| 06012 | Fugloy | 62.3195 | -6.3205 | 54.0 | 4 | 1999-05-14 | 2024-11-22 |
| 06013 | Klaksvik Heliport | 62.2178 | -6.5766 | 80.162 | 3 | 2009-05-18 | 2024-11-22 |
| 06014 | Eidi | 62.2995 | -7.0740 | 176.5 | 3 | 2022-05-25 | 2024-06-14 |

Note: Station 06009 had prior names Akraberg Fyr and 06011 had a period as Havn. Current `status=Active` appears also on old historical revisions; use `validFrom`/`validTo` to identify effective record, not status alone.

Available `parameterId` lists include temp_dry, wind_speed, pressure_at_sea for all seven; precip_past1h is listed for 06009, 06011, 06012 and 06014. This does **not** demonstrate actual data availability for any particular day.

Before verification:
- Count actual returned observations by station/parameter/date and inspect recent observations.
- Preserve time-dependent station metadata and unknown sensor heights.
- Check wind measurement definitions before comparing with models' 10 m winds.
- Validate unit metadata and DMI quality flags, avoid interpolating missing observations into 'ground truth'.
- Do not mistake the output of candidate discovery for actual forecasts or forecast accuracy.
