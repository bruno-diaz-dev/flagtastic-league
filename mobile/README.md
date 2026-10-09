# Flagtastic League Mobile

Expo application for players and referees. Player mode includes:

1. `Inicio`: team position, next game, season summary, and shortcuts.
2. `Posiciones`: the signed-in player's division standings.
3. `Lideres`: the six official individual leaderboards.
4. `Mis Stats`: the signed-in player's accumulated offensive and defensive data.

Referee mode includes `Inicio` (next assignment and totals), `Mi agenda`
(pending/postponed games, time, field, position and crew), and `Historial`
(completed assignments, results and participation by position/jornada).
`Mi perfil` supports logout and switching modes for accounts with both roles.
Referees start in referee mode, including after restoring a saved session.
Game detail and profile administration open the web application, where a
separate browser login may be required.

Assignments use the protected `/api/games/mine/referee` endpoint and profile
data comes from `/api/referees/me`. Deploy the updated `/api/auth/mobile/login`
backend before testing referee-only sign-in against production. For local
testing, point `EXPO_PUBLIC_API_URL` to the reachable development backend.

## Local development

```powershell
cd mobile
npm ci
$env:EXPO_PUBLIC_API_URL="http://127.0.0.1:8000"
npm start
```

Use `i` for the iOS simulator, `a` for Android, or scan the QR code with Expo
Go. A physical phone cannot reach the computer through `127.0.0.1`; use the
computer's LAN address for `EXPO_PUBLIC_API_URL` in that case.

The default API URL is `https://flagtastic.online`, the canonical domain, so
native login requests do not require a cross-domain redirect. Authentication
uses the normal player or referee email and password. The API issues a revocable 12-hour
Bearer session, which the native client keeps in the platform secure store.

## Validation and builds

```powershell
npm run typecheck
npx expo-doctor
npx eas-cli build --platform android
npx eas-cli build --platform ios
```

Store builds require an Expo account and the corresponding Google Play or Apple
Developer account. No database is embedded in the app: every screen reads the
same FastAPI and Supabase-backed data as the web application.

## APK distribution and remote updates

Project: `@brucie/flagtastic-league-mobile`. The `apk` build profile produces
a standalone, internally distributed Android APK on the `production` update
channel. It does not need Metro or Expo Go. EAS manages its signing key and
increments the Android version code remotely.

```powershell
# Build a shareable APK (run from mobile/)
npx eas-cli@latest build --platform android --profile apk

# Publish tested JavaScript/assets to installed production APKs
npx eas-cli@latest update --channel production --platform android --environment production --message "Describe the changes"
```

The app checks for updates on launch. With the default update behavior, a
downloaded update is applied on the following app restart. An older APK that
does not include expo-updates must be replaced with this enabled build first.
Keep the same Android signing key for subsequent APKs.

The runtime uses the `appVersion` policy: increment `expo.version` in app.json
and create a new APK whenever native dependencies, permissions, SDK version,
or native configuration change. Do not send incompatible native changes to
an existing runtime. Use the `preview` profile/channel to test updates before
publishing them to `production`.
