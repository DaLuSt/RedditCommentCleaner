package com.redditcommentcleaner.api

import com.redditcommentcleaner.model.TokenResponse
import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.POST

interface RedditAuthService {

    /** Exchange an authorization code for tokens (PKCE flow). */
    @FormUrlEncoded
    @POST("api/v1/access_token")
    suspend fun fetchToken(
        @Field("grant_type")    grantType: String = "authorization_code",
        @Field("code")          code: String,
        @Field("redirect_uri")  redirectUri: String,
        @Field("code_verifier") codeVerifier: String
    ): TokenResponse

    /** Exchange a refresh token for a new access token. */
    @FormUrlEncoded
    @POST("api/v1/access_token")
    suspend fun refreshToken(
        @Field("grant_type")    grantType: String = "refresh_token",
        @Field("refresh_token") refreshToken: String
    ): TokenResponse
}
