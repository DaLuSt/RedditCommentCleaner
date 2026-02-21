package com.redditcommentcleaner.auth

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.browser.customtabs.CustomTabsIntent
import com.redditcommentcleaner.BuildConfig
import com.redditcommentcleaner.databinding.ActivityLoginBinding
import com.redditcommentcleaner.util.PkceHelper

/**
 * Shows a "Login with Reddit" button that opens Reddit's OAuth consent page
 * in a Chrome Custom Tab. The redirect is caught by OAuthCallbackActivity.
 *
 * The PKCE code_verifier is stored in a companion object so OAuthCallbackActivity
 * can retrieve it for the token exchange.
 */
class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)
        supportActionBar?.hide()

        binding.btnLogin.setOnClickListener { openRedditAuth() }
    }

    private fun openRedditAuth() {
        val verifier  = PkceHelper.generateCodeVerifier()
        val challenge = PkceHelper.generateCodeChallenge(verifier)
        val state     = PkceHelper.generateState()

        pendingCodeVerifier = verifier
        pendingState        = state

        val url = Uri.Builder()
            .scheme("https").authority("www.reddit.com")
            .path("api/v1/authorize")
            .appendQueryParameter("client_id",             BuildConfig.REDDIT_CLIENT_ID)
            .appendQueryParameter("response_type",         "code")
            .appendQueryParameter("state",                 state)
            .appendQueryParameter("redirect_uri",          BuildConfig.REDIRECT_URI)
            .appendQueryParameter("duration",              "permanent")
            .appendQueryParameter("scope",                 BuildConfig.OAUTH_SCOPES)
            .appendQueryParameter("code_challenge",        challenge)
            .appendQueryParameter("code_challenge_method", "S256")
            .build()

        CustomTabsIntent.Builder().build().launchUrl(this, url)
    }

    companion object {
        /** Shared with OAuthCallbackActivity — lives only for the duration of the login flow. */
        var pendingCodeVerifier: String? = null
        var pendingState: String?        = null
    }
}
