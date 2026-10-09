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

The EAS project is `@brucies-team/flagtastic-league-mobile`, with project ID
`49015503-598d-4ba6-98de-51126bdf83f3`. Team ownership keeps signing credentials
and build history independent of one developer account. The bundle identifiers
are `com.flagtastic.league` on both platforms; Apple registration still requires
the team's Apple Developer credentials.

## Real-User Beta

Build Android with `eas build --platform android --profile preview`. Share the
completed build's installation page with testers so they can download the APK.
Android may ask them to allow installation from their browser. Testers sign in
with their existing production player account; administrator-only and
representative-only accounts cannot sign in to this player app.

The preview profile explicitly uses `https://flagtastic.online`. It is a real
production-data beta, not a seeded demo. The app reads player dashboards,
standings, games and leaderboards. Profile actions open the production website.
Do not package local development environment files or substitute a LAN address
when creating a distributable build.

For iPhone, use the production iOS profile and distribute through TestFlight.
A paid Apple Developer membership, signing credentials and an App Store Connect
app record are required. External testers install Apple's TestFlight app and
join through an invitation or public testing link after the required beta review.
An iOS simulator build cannot be installed on a real iPhone. Ad hoc distribution
also requires Apple credentials and advance registration of each test device.

Channels are currently named in the build profiles, but `expo-updates` is not
installed. Distribute a new binary for fixes; do not promise over-the-air updates.

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
