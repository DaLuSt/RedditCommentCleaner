# Android App — Setup Guide

## Prerequisites

- Android Studio Hedgehog (2023.1) or newer
- JDK 17
- A Reddit account with a registered **installed app**

---

## 1. Register a Reddit "installed app"

1. Go to <https://www.reddit.com/prefs/apps>
2. Click **Create another app…**
3. Choose type **installed app** (not "script")
4. Set **redirect URI** to exactly: `redditcommentcleaner://auth`
5. Save — note the **client ID** (the string under your app name)

---

## 2. Add your client ID to `local.properties`

`local.properties` lives in the `android/` directory and is already listed in `.gitignore` — **never commit it**.

```properties
# android/local.properties
sdk.dir=/path/to/your/android/sdk
reddit.client_id=abc123xyz
```

The build script reads `reddit.client_id` automatically. Do **not** edit `app/build.gradle` to add the client ID directly.

---

## 3. Build & run (debug)

```bash
cd android
./gradlew assembleDebug
# install on connected device / emulator:
adb install app/build/outputs/apk/debug/app-debug.apk
```

Or open the `android/` directory in Android Studio and click **Run**.

---

## 4. Build a release APK / AAB for Play Store

### 4a. Generate a release keystore (one-time setup)

```bash
keytool -genkeypair -v \
  -keystore my-release-key.jks \
  -keyalg RSA -keysize 2048 \
  -validity 10000 \
  -alias my-key-alias
```

Move the resulting `.jks` file somewhere safe and **outside** the repo. Never commit it.

### 4b. Create `keystore.properties`

Create `android/keystore.properties` (already in `.gitignore`):

```properties
storeFile=/absolute/path/to/my-release-key.jks
storePassword=your_store_password
keyAlias=my-key-alias
keyPassword=your_key_password
```

### 4c. Build the signed AAB

```bash
cd android
./gradlew bundleRelease
# Output: app/build/outputs/bundle/release/app-release.aab
```

Or build a signed APK:

```bash
./gradlew assembleRelease
# Output: app/build/outputs/apk/release/app-release.apk
```

---

## 5. Play Store listing requirements

Before submitting to the Play Store you will also need:

| Requirement | Where |
|---|---|
| **Privacy policy URL** | Host `PRIVACY_POLICY.md` (e.g. GitHub Pages) and paste the URL in the Play Console listing |
| **Store listing icon** | 512×512 PNG (export from the vector at `res/drawable/ic_launcher_foreground.xml`) |
| **Feature graphic** | 1024×500 PNG (create separately) |
| **Screenshots** | Minimum 2 per supported form factor |

---

## How the app works

| Step | What happens |
|------|--------------|
| First launch | Routed to the Login screen |
| Tap "Login with Reddit" | Reddit's OAuth consent page opens in a Chrome Custom Tab |
| User approves | Reddit redirects to `redditcommentcleaner://auth?code=…` |
| App exchanges code for token | PKCE S256 flow; tokens stored in EncryptedSharedPreferences |
| Dashboard loads | All comments and posts fetched with full pagination |
| Filter + select | Score ≤ N, age ≥ N days; Select All / None / Matching |
| Delete | Each item is edited to `"."` then deleted; progress shown inline |
| Logout | Tokens cleared; back to Login screen |

---

## OAuth scopes requested

| Scope | Purpose |
|-------|---------|
| `identity` | Read username |
| `history`  | List comments and posts |
| `edit`     | Overwrite item body with `"."` before deletion |

---

## Project structure

```
android/
├── app/build.gradle               ← dependencies, signing config, buildConfigFields
├── app/proguard-rules.pro         ← R8/ProGuard rules for release builds
├── app/src/main/
│   ├── AndroidManifest.xml
│   ├── java/com/redditcommentcleaner/
│   │   ├── MainActivity.kt        ← routes to Login or Dashboard
│   │   ├── auth/
│   │   │   ├── LoginActivity.kt   ← opens OAuth URL in Chrome Custom Tab
│   │   │   └── OAuthCallbackActivity.kt  ← handles redirect, exchanges code
│   │   ├── api/
│   │   │   ├── RedditApiClient.kt ← OkHttp/Retrofit setup + token refresh
│   │   │   ├── RedditAuthService.kt  ← token exchange endpoints
│   │   │   └── RedditApiService.kt   ← comments, posts, edit, delete
│   │   ├── model/RedditModels.kt  ← data classes
│   │   ├── dashboard/
│   │   │   ├── DashboardActivity.kt  ← main screen
│   │   │   ├── DashboardViewModel.kt ← load, filter, delete logic
│   │   │   └── ItemAdapter.kt     ← RecyclerView adapter
│   │   └── util/
│   │       ├── TokenStorage.kt    ← EncryptedSharedPreferences wrapper
│   │       └── PkceHelper.kt      ← PKCE code_verifier/challenge generation
│   └── res/
│       ├── drawable/              ← ic_launcher_background/foreground (vector)
│       ├── layout/                ← activity and item layouts
│       ├── mipmap-anydpi-v26/     ← adaptive icon (ic_launcher, ic_launcher_round)
│       ├── values/                ← colors, strings, themes
│       └── xml/                   ← network_security_config.xml
├── PRIVACY_POLICY.md              ← host this URL in Play Console listing
└── SETUP.md                       ← this file
```
