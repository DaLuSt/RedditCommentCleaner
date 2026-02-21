package com.redditcommentcleaner.model

import com.google.gson.annotations.SerializedName
import java.util.concurrent.TimeUnit

// ── API response wrappers ─────────────────────────────────────────────────────

data class RedditListingResponse<T>(
    val data: ListingData<T>
)

data class ListingData<T>(
    val after: String?,
    val children: List<ListingChild<T>>
)

data class ListingChild<T>(
    val kind: String,
    val data: T
)

data class MeResponse(
    val name: String,
    val id: String,
    @SerializedName("icon_img") val iconImg: String?
)

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("refresh_token") val refreshToken: String?,
    @SerializedName("expires_in") val expiresIn: Int,
    @SerializedName("token_type") val tokenType: String,
    val scope: String
)

// ── Reddit item data classes ───────────────────────────────────────────────────

data class CommentData(
    val id: String,
    val name: String,          // fullname e.g. "t1_abcdef"
    val body: String,
    val score: Int,
    @SerializedName("created_utc") val createdUtc: Double,
    val subreddit: String,
    @SerializedName("link_title") val linkTitle: String?
)

data class PostData(
    val id: String,
    val name: String,          // fullname e.g. "t3_abcdef"
    val title: String,
    val score: Int,
    @SerializedName("created_utc") val createdUtc: Double,
    val subreddit: String,
    @SerializedName("is_self") val isSelf: Boolean
)

// ── UI model ─────────────────────────────────────────────────────────────────

sealed class RedditItem(open var selected: Boolean = false) {
    data class Comment(val data: CommentData, override var selected: Boolean = false) : RedditItem(selected)
    data class Post(val data: PostData, override var selected: Boolean = false) : RedditItem(selected)

    val name: String get() = when (this) {
        is Comment -> data.name
        is Post    -> data.name
    }

    val score: Int get() = when (this) {
        is Comment -> data.score
        is Post    -> data.score
    }

    val createdUtc: Double get() = when (this) {
        is Comment -> data.createdUtc
        is Post    -> data.createdUtc
    }

    val subreddit: String get() = when (this) {
        is Comment -> data.subreddit
        is Post    -> data.subreddit
    }

    /** Age of the item in whole days. */
    val ageDays: Long get() {
        val nowSec = System.currentTimeMillis() / 1000L
        return TimeUnit.SECONDS.toDays(nowSec - createdUtc.toLong())
    }
}
