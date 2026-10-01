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

The default API URL is `https://flagtastic-league.vercel.app`. Authentication
uses the normal player email and password. The API issues a revocable 12-hour
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
