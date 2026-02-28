# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| < 1.0   | &#x2717; |
| 1.0     | &#x2717; |
| 1.8     | &#x2713; |

## Reporting a Vulnerability

Open a **pull request** or **GitHub issue** describing the vulnerability.

For sensitive disclosures that should not be public, you can also reach the maintainer via the email address listed on the GitHub profile.

### Notes on attack surface

- **CLI scripts** communicate only with the Reddit API via PRAW. They do not open any network ports, start any servers, or call any third-party services other than Reddit and (optionally) Google Drive.
- **Web app** (`web/app.py`) exposes a local Flask server on port 5000. It should only be run on a trusted machine and network. It is not hardened for public internet exposure.
- **Android app** uses Reddit's OAuth 2.0 PKCE flow with the official Reddit API. Tokens are stored in EncryptedSharedPreferences.
- **Credentials** (Reddit password, API secret) are never written to disk by the web app or Android app; only the CLI scripts read them from `Credentials.txt`.

Always review the code of the tools you are using before running them with your account credentials.
