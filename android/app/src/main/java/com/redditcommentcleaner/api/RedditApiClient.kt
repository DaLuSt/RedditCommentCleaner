package com.redditcommentcleaner.api

import android.content.Context
import android.util.Base64
import com.redditcommentcleaner.BuildConfig
import com.redditcommentcleaner.util.TokenStorage
import kotlinx.coroutines.runBlocking
import okhttp3.Credentials
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

private const val BASE_URL      = "https://oauth.reddit.com/"
private const val AUTH_BASE_URL = "https://www.reddit.com/"

object RedditApiClient {

    /** Retrofit for authenticated API calls (oauth.reddit.com). */
    fun apiService(context: Context): RedditApiService {
        val tokenStorage = TokenStorage(context)
        val client = OkHttpClient.Builder()
            .addInterceptor { chain ->
                // Refresh token if near expiry
                if (tokenStorage.isTokenExpired() && !tokenStorage.refreshToken.isNullOrBlank()) {
                    runBlocking {
                        runCatching {
                            val resp = authService().refreshToken(
                                refreshToken = tokenStorage.refreshToken!!
                            )
                            tokenStorage.accessToken  = resp.accessToken
                            tokenStorage.tokenExpiryMs = System.currentTimeMillis() + resp.expiresIn * 1000L
                        }
                    }
                }
                val request = chain.request().newBuilder()
                    .header("Authorization", "Bearer ${tokenStorage.accessToken}")
                    .header("User-Agent", userAgent(tokenStorage.username ?: "unknown"))
                    .build()
                chain.proceed(request)
            }
            .addInterceptor(loggingInterceptor())
            .build()

        return Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(RedditApiService::class.java)
    }

    /** Retrofit for token exchange (www.reddit.com) — uses HTTP Basic auth. */
    fun authService(): RedditAuthService {
        val client = OkHttpClient.Builder()
            .addInterceptor { chain ->
                val credential = Credentials.basic(BuildConfig.REDDIT_CLIENT_ID, "")
                val request = chain.request().newBuilder()
                    .header("Authorization", credential)
                    .header("User-Agent", userAgent("anonymous"))
                    .build()
                chain.proceed(request)
            }
            .addInterceptor(loggingInterceptor())
            .build()

        return Retrofit.Builder()
            .baseUrl(AUTH_BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(RedditAuthService::class.java)
    }

    private fun userAgent(username: String) =
        "android:com.redditcommentcleaner:v1.0 (by /u/$username)"

    private fun loggingInterceptor() = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BASIC
    }
}
