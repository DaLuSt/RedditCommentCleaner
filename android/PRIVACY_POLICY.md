# Privacy Policy — Reddit Comment Cleaner (Android)

**Last updated: 2026-02-28**

## Overview

Reddit Comment Cleaner is a tool that lets you bulk-delete your own Reddit comments and posts. This policy explains what data the app accesses, how it is used, and how it is stored.

## Data accessed

The app requests the following Reddit OAuth scopes when you log in:

| Scope | Purpose |
|-------|---------|
| `identity` | Read your Reddit username to display in the dashboard |
| `history` | List your own comments and posts so you can review them |
| `edit` | Overwrite each item with `"."` before deletion, preventing content-scraping tools from capturing the original text |

The app does **not** request `vote`, `submit`, `read`, `subscribe`, or any moderation scopes.

## Data stored on your device

| Data | Storage | Cleared when |
|------|---------|--------------|
| OAuth access token | EncryptedSharedPreferences (AES-256-GCM) | You tap "Log out" |
| OAuth refresh token | EncryptedSharedPreferences (AES-256-GCM) | You tap "Log out" |
| Reddit username | EncryptedSharedPreferences | You tap "Log out" |
| Token expiry timestamp | EncryptedSharedPreferences | You tap "Log out" |

No data is written to external storage or shared with any third party.

## Data transmitted

All network requests go directly to the Reddit API (`oauth.reddit.com`, `www.reddit.com`). No data is sent to any server operated by this app's developer.

## Data not collected

- The app does not collect analytics, crash reports, or usage telemetry.
- No advertising SDKs are included.
- No data is shared with advertisers or data brokers.

## Third-party services

The app communicates only with Reddit's official API. Reddit's own privacy policy applies to that communication: <https://www.reddit.com/policies/privacy-policy>

## Changes to this policy

If the app's data practices change, this document will be updated and the "Last updated" date above will be revised.

## Contact

If you have questions about this policy, open an issue at the project's GitHub repository.
