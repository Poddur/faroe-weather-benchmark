# Deployment gate

Current state: **not deployed**. No Cloud Run Job or Cloud Scheduler trigger has been created by ChatGPT.

## Existing accounts
The user's past Google Cloud configuration was reported as:
- candidate project: `project-81168655-0a30-4c54-a20` (unverified now)
- candidate region: `europe-west1`
- existing service: `sementicx-worker` (must not be modified)

Do not assume that the current Google account, billing status or permissions match these values. Check in Google Cloud Console or Cloud Shell.

## Minimum checks before execution
1. Verified real Faroese station metadata and DMI API access.
2. Working live source downloads and stable model issue timestamps.
3. Dedicated service account with bucket-scoped permissions.
4. Storage budget alert, retained-file naming scheme, and retry strategy.
5. Run a one-off Cloud Run Job and inspect logs and archived objects.
6. Only then create a Scheduler trigger; verify expected frequency and costs.

## WeatherNext
Google WeatherNext 3 approval is pending. Integrate only after confirming dataset identity and schema.

## Public repository warning
The GitHub repository was created as **Public**. Do not commit any credentials or secret material. If desired, change visibility to Private under Repository Settings > General > Danger Zone.
