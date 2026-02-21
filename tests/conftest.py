"""
Shared pytest fixtures and stubs.

google-auth / google-api-python-client are not installed in the test
environment (they are only needed for the optional Drive upload feature).
We stub them out before any test file imports drive_upload so the module
can be imported without errors.
"""

import sys
import types
import unittest.mock as mock

# ── Stub google packages ──────────────────────────────────────────────────────
def _stub_google():
    google = types.ModuleType("google")
    google.oauth2 = types.ModuleType("google.oauth2")
    creds_mod = types.ModuleType("google.oauth2.service_account")

    class FakeCreds:
        @classmethod
        def from_service_account_info(cls, info, scopes=None):
            return cls()

    creds_mod.Credentials = FakeCreds
    google.oauth2.service_account = creds_mod

    googleapiclient = types.ModuleType("googleapiclient")
    discovery_mod = types.ModuleType("googleapiclient.discovery")
    discovery_mod.build = mock.MagicMock(return_value=mock.MagicMock())
    googleapiclient.discovery = discovery_mod

    http_mod = types.ModuleType("googleapiclient.http")
    http_mod.MediaFileUpload = mock.MagicMock()
    googleapiclient.http = http_mod

    sys.modules.setdefault("google", google)
    sys.modules.setdefault("google.oauth2", google.oauth2)
    sys.modules.setdefault("google.oauth2.service_account", creds_mod)
    sys.modules.setdefault("googleapiclient", googleapiclient)
    sys.modules.setdefault("googleapiclient.discovery", discovery_mod)
    sys.modules.setdefault("googleapiclient.http", http_mod)


_stub_google()
