package com.redditcommentcleaner.api

import com.redditcommentcleaner.model.CommentData
import com.redditcommentcleaner.model.ListingChild
import com.redditcommentcleaner.model.MeResponse
import com.redditcommentcleaner.model.PostData
import com.redditcommentcleaner.model.RedditListingResponse
import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface RedditApiService {

    @GET("api/v1/me")
    suspend fun getMe(): MeResponse

    @GET("user/{username}/comments")
    suspend fun getComments(
        @Path("username") username: String,
        @Query("limit")   limit: Int = 100,
        @Query("after")   after: String? = null
    ): RedditListingResponse<CommentData>

    @GET("user/{username}/submitted")
    suspend fun getPosts(
        @Path("username") username: String,
        @Query("limit")   limit: Int = 100,
        @Query("after")   after: String? = null
    ): RedditListingResponse<PostData>

    @FormUrlEncoded
    @POST("api/editusertext")
    suspend fun editItem(
        @Field("thing_id") thingId: String,
        @Field("text")     text: String = "."
    ): Any

    @FormUrlEncoded
    @POST("api/del")
    suspend fun deleteItem(
        @Field("id") fullname: String
    ): Any
}
