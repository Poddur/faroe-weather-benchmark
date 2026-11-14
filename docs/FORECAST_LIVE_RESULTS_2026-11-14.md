# Live forecast probe: ECMWF IFS and HARMONIE — 2026-11-14

**Evidence:** [GitHub Actions run 43618867705](https://github.com/Poddur/faroe-weather-benchmark/actions/runs/43618867705). Both independent jobs succeeded.

## ECMWF IFS

- Artifact: `ecmwf-live-probe-diagnostics`, ID **14123420918** (expires 2026-11-28).
- Source: ECMWF open-data IFS, 0.25 degree (pilot; NOT final 0.1-degree benchmark).
- Issue time: **2026-11-14 00:00 UTC**; lead: **6 h**; verification: **2026-11-14 06:00 UTC**.
- Raw downloaded GRIB2 size: **312,214 bytes**; SHA-256: `22113b5eaf7456d804ac6de75c55695c9dda7b97bb3ded8b185d85a93da980ce`.
- The original GRIB was processed on GitHub but **not retained in the uploaded artifact**; only manifest/sample values survived.

| Station | ID | Model 2m temperature, °C | selected grid latitude | selected grid longitude |
|---|---|---:|---:|---:|
| Suður | 06009 | 4.92794 | 61.50 | -6.75 |
| Tórshavn | 06011 | 5.17794 | 62.00 | -6.75 |
| Eiði | 06014 | 1.42794 | 62.25 | -7.00 |

## DMI HARMONIE

- Artifact: `harmonie-live-probe-diagnostics`, ID **14122879804** (expires 2026-11-28).
- The catalogue lists both `harmonie_dini_sf` and `harmonie_ig_sf`. The exploratory `harmonie_nea_sf` returned HTTP 404.
- The `/instances` endpoint returned HTTP 200. The **singular** `/instance` endpoint returned HTTP 404, and must NOT be used.
- Latest `/position` response for DINI: **61 hourly features** per station, first valid time **2026-11-14 12:00 UTC**. Temperature (Kelvin) and 10m wind (m/s) are present. The source instance catalogue identifies a run ID `2026-11-14T120000Z` at the time of the probe. Use an instance-qualified endpoint for provenance in production.

| Station | DINI returned grid distance, km | IG returned grid distance, km |
|---|---:|---:|
| Suður 06009 | 0.18 | 238.14 |
| Tórshavn 06011 | 0.48 | 192.30 |
| Eiði 06014 | 0.99 | 155.23 |

These distances were calculated from DMI's station coordinates and the grid-point GeoJSON coordinates. **IG returned HTTP 200 but a geographically distant point**: do not treat IG as a local Faroese station forecast. Restrict pilot to `harmonie_dini_sf`, with an enforced distance limit.

## Scientific implications

1. Both real forecast sources are accessible from GitHub runners.
2. **No ECMWF-vs-HARMONIE skill comparison is justified by this run**: their sampled issue times and valid times do not match and no aligned DMI observations were joined.
3. Avoid confusing a GitHub job success with model accuracy.
4. Validate physical units, station instrumentation, and effective-dated metadata.
5. Capture actual issue IDs, raw forecast bytes, SHA-256, and observations for matched valid times before scoring.
6. Keep manual collection until long-lived storage and budget limits are established.

**Deployment status:** No permanent collector, Cloud Run service/job, bucket or scheduled workflow has been activated.
