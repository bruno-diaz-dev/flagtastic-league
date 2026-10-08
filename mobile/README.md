# Flagtastic League Mobile

Expo application for the league's focused player experience. It intentionally
contains exactly four native views:

1. `Inicio`: team position, next game, season summary, and shortcuts.
2. `Posiciones`: the signed-in player's division standings.
3. `Lideres`: the six official individual leaderboards.
4. `Mis Stats`: the signed-in player's accumulated offensive and defensive data.

The persistent `Perfil` action opens the production web dashboard. Game detail,
calendar administration, registration, roster management, and every other
workflow also remain in the web application; the mobile app does not duplicate
them.

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

The default API URL is `https://flagtastic.online`. Authentication
uses the normal player email and password. The API issues a revocable 12-hour
Bearer session, which the native client keeps in the platform secure store.

## Validation and builds

```powershell
npm run typecheck
npx expo-doctor
npx eas-cli build --platform android --profile preview
npx eas-cli build --platform ios --profile preview
```

The `preview` profile creates an installable Android APK or an iOS ad hoc build
and always targets the production API. Use it for stakeholder testing before
creating store binaries. The `production` profile creates store-ready artifacts:

```powershell
npx eas-cli build --platform all --profile production
npx eas-cli submit --platform android --profile production
npx eas-cli submit --platform ios --profile production
```

The EAS project must first be linked to the Expo organization that will own the
app. Do not initialize it under a personal account if the league organization is
intended to own credentials, builds, and future store submissions.

Store builds require an Expo account and the corresponding Google Play or Apple
Developer account. No database is embedded in the app: every screen reads the
same FastAPI and Supabase-backed data as the web application.
