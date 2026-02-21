package com.redditcommentcleaner.util

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Persists OAuth tokens in EncryptedSharedPreferences (AES-256-GCM key in the Android Keystore).
 */
class TokenStorage(context: Context) {

    private val prefs = EncryptedSharedPreferences.create(
        context,
        "reddit_tokens",
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

    var accessToken: String?
        get() = prefs.getString(KEY_ACCESS_TOKEN, null)
        set(value) = prefs.edit().putString(KEY_ACCESS_TOKEN, value).apply()

    var refreshToken: String?
        get() = prefs.getString(KEY_REFRESH_TOKEN, null)
        set(value) = prefs.edit().putString(KEY_REFRESH_TOKEN, value).apply()

    var username: String?
        get() = prefs.getString(KEY_USERNAME, null)
        set(value) = prefs.edit().putString(KEY_USERNAME, value).apply()

    /** Millisecond epoch at which the access token expires. */
    var tokenExpiryMs: Long
        get() = prefs.getLong(KEY_EXPIRY_MS, 0L)
        set(value) = prefs.edit().putLong(KEY_EXPIRY_MS, value).apply()

    fun isLoggedIn(): Boolean = !accessToken.isNullOrBlank()

    fun isTokenExpired(): Boolean = System.currentTimeMillis() >= tokenExpiryMs - 60_000L

    fun clear() {
        prefs.edit().clear().apply()
    }

    companion object {
        private const val KEY_ACCESS_TOKEN  = "access_token"
        private const val KEY_REFRESH_TOKEN = "refresh_token"
        private const val KEY_USERNAME      = "username"
        private const val KEY_EXPIRY_MS     = "expiry_ms"
    }
}
