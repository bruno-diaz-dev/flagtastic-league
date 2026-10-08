# Mobile Release

The Expo client is a focused player application. FastAPI remains the only API,
PostgreSQL remains the only database, and `https://flagtastic.online` is the
canonical production origin for both API calls and web handoffs.

## Distribution Stages

1. Local development uses Expo Go and an explicit `EXPO_PUBLIC_API_URL`.
2. The EAS `preview` profile creates an Android APK or an iOS ad hoc build for
   direct stakeholder installation. Preview builds call the production API.
3. The EAS `production` profile creates an Android App Bundle and iOS archive
   for Google Play internal testing and TestFlight before public release.
4. Store submission uses the `production` submit profile after listing copy,
   screenshots, support contact, privacy answers and credentials are complete.

EAS project ownership must be selected deliberately before initialization. A
team-owned Expo project keeps signing credentials and build history independent
of one developer account. The bundle identifiers are `com.flagtastic.league` on
both platforms and must be confirmed as available before store registration.

## Release Checks

- `npm ci`
- `npm run typecheck`
- `npx expo-doctor`
- Validate login, token expiry, logout, pull-to-refresh and multi-team switching.
- Validate the production `/live` endpoint and at least one public API request.
- Install the preview binary on a physical Android device before store builds.
- Register iOS test device UDIDs before creating an ad hoc iOS preview.
- Confirm the public privacy page at `https://flagtastic.online/privacy`.

Internal builds are not a substitute for store testing. Android production
builds should move through Google Play internal testing; iOS builds should move
through TestFlight. Native dependency or permission changes require a new binary.
