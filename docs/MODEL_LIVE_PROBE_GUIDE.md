# ECMWF / HARMONIE live verification gate (2026-11-14)

Purpose: Establish that the live forecast APIs genuinely serve the three DMI pilot station coordinates before scheduling any collector. No forecast accuracy results exist yet.

## Manual run
GitHub Actions > Live forecast probes — ECMWF and HARMONIE > Run workflow (main).

Two independent jobs:
- ECMWF: Downloads one recent IFS 2m-temperature GRIB (6h lead, 0.25 degree preliminary resolution) and extracts three nearest-grid values with a provenance manifest. The 0.25-degree pilot avoids unnecessarily large datasets. Production can later be upgraded to 0.1 degree.
- HARMONIE: Queries DMI EDR collection catalogue, metadata and actual /position response for three sites. Tests harmonie_nea_sf, harmonie_dini_sf, harmonie_ig_sf and lists available instances; archives HTTP responses even on failures. First probe deliberately does not label a latest-run response with a guessed issue time.

When a job fails, download its associated artifact: a failure is still useful evidence of missing coverage, outdated endpoint, or download/schema problems.

## Validation required
1. Verify forecast issue time against source model run, not system clock.
2. Verify whether HARMONIE covers the Faroes; a collection's existence does not imply coverage.
3. Compare identical forecast leads, valid times, station IDs and units with observations.
4. Preserve raw hashes, source URLs and exception diagnostics.
5. Keep the job MANUAL until verified and storage retention/costs are configured.

DMI EDR retains a short live forecast history; GitHub Actions artifacts are temporary. This manual probe is not permanent archiving.

## Source references
- https://www.dmi.dk/friedata/dokumentation/forecast-data-edr-api
- https://www.dmi.dk/friedata/dokumentation/data/weather-model-harmonie-nea-edr-api-parameter-list
- https://github.com/ecmwf/ecmwf-opendata

Deployment state: no Cloud Run job, storage bucket or scheduler has been created.
