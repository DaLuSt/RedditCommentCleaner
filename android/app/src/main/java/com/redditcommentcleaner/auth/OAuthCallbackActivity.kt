package com.redditcommentcleaner.auth

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.redditcommentcleaner.BuildConfig
import com.redditcommentcleaner.api.RedditApiClient
import com.redditcommentcleaner.dashboard.DashboardActivity
import com.redditcommentcleaner.databinding.ActivityOauthCallbackBinding
import com.redditcommentcleaner.util.TokenStorage
import kotlinx.coroutines.launch

/**
 * Transparent activity that intercepts the OAuth redirect URI
 * (redditcommentcleaner://auth?code=...&state=...).
 *
 * 1. Validates the state parameter.
 * 2. Exchanges the code for tokens.
 * 3. Fetches the authenticated user's username.
 * 4. Stores everything and launches DashboardActivity.
 */
class OAuthCallbackActivity : AppCompatActivity() {

    private lateinit var binding: ActivityOauthCallbackBinding
    private lateinit var tokenStorage: TokenStorage

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityOauthCallbackBinding.inflate(layoutInflater)
        setContentView(binding.root)
        supportActionBar?.hide()

        tokenStorage = TokenStorage(this)
        handleIntent(intent)
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        intent?.let { handleIntent(it) }
    }

    private fun handleIntent(intent: Intent) {
        val uri = intent.data ?: return finish()

        val error = uri.getQueryParameter("error")
        if (error != null) {
            toast("Reddit OAuth error: $error")
            goToLogin()
            return
        }

        val code  = uri.getQueryParameter("code")  ?: run { goToLogin(); return }
        val state = uri.getQueryParameter("state") ?: run { goToLogin(); return }

        if (state != LoginActivity.pendingState) {
            toast("OAuth state mismatch — possible CSRF attack")
            goToLogin()
            return
        }

        val verifier = LoginActivity.pendingCodeVerifier ?: run { goToLogin(); return }
        LoginActivity.pendingCodeVerifier = null
        LoginActivity.pendingState = null

        lifecycleScope.launch {
            runCatching {
                val authService = RedditApiClient.authService()
                val tokenResp = authService.fetchToken(
                    code         = code,
                    redirectUri  = BuildConfig.REDIRECT_URI,
                    codeVerifier = verifier
                )
                tokenStorage.accessToken   = tokenResp.accessToken
                tokenStorage.refreshToken  = tokenResp.refreshToken
                tokenStorage.tokenExpiryMs = System.currentTimeMillis() + tokenResp.expiresIn * 1000L

                // Fetch and store the username
                val me = RedditApiClient.apiService(this@OAuthCallbackActivity).getMe()
                tokenStorage.username = me.name

                startActivity(Intent(this@OAuthCallbackActivity, DashboardActivity::class.java))
                finish()
            }.onFailure {
                toast("Login failed: ${it.message}")
                goToLogin()
            }
        }
    }

    private fun goToLogin() {
        startActivity(Intent(this, LoginActivity::class.java))
        finish()
    }

    private fun toast(msg: String) = Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
}
