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

## 2. Put your client ID in the build config

Open `app/build.gradle` and replace `YOUR_CLIENT_ID`:

```groovy
buildConfigField "String", "REDDIT_CLIENT_ID", '"abc123xyz"'   // ← your client ID here
```

---

## 3. Build & run

```bash
cd android
./gradlew assembleDebug
# install on connected device / emulator:
adb install app/build/outputs/apk/debug/app-debug.apk
```

Or open the `android/` directory in Android Studio and click **Run**.

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
| `edit`     | Overwrite item body with `"."` |
| `vote`     | (reserved for future score filtering) |

---

## Project structure

```
android/
├── app/build.gradle               ← dependencies & buildConfigFields
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
│       ├── layout/                ← activity and item layouts
│       └── values/                ← colors, strings, themes
└── SETUP.md                       ← this file
```
