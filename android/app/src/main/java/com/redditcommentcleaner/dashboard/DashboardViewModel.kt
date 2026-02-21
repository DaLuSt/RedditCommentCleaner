package com.redditcommentcleaner.dashboard

import android.content.Context
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.redditcommentcleaner.api.RedditApiClient
import com.redditcommentcleaner.model.CommentData
import com.redditcommentcleaner.model.PostData
import com.redditcommentcleaner.model.RedditItem
import com.redditcommentcleaner.util.TokenStorage
import kotlinx.coroutines.launch

sealed class UiState {
    object Loading : UiState()
    object Idle    : UiState()
    data class Error(val message: String) : UiState()
    data class DeleteProgress(val done: Int, val total: Int) : UiState()
    object DeleteDone : UiState()
}

class DashboardViewModel(private val context: Context) : ViewModel() {

    private val api     by lazy { RedditApiClient.apiService(context) }
    private val storage by lazy { TokenStorage(context) }

    private val _comments  = MutableLiveData<List<RedditItem.Comment>>(emptyList())
    val comments: LiveData<List<RedditItem.Comment>> = _comments

    private val _posts     = MutableLiveData<List<RedditItem.Post>>(emptyList())
    val posts: LiveData<List<RedditItem.Post>> = _posts

    private val _uiState   = MutableLiveData<UiState>(UiState.Idle)
    val uiState: LiveData<UiState> = _uiState

    val username: String? get() = storage.username

    // ── Load all items ────────────────────────────────────────────────────────

    fun loadAll() {
        _uiState.value = UiState.Loading
        viewModelScope.launch {
            runCatching {
                val username = storage.username ?: error("Not logged in")
                _comments.postValue(fetchAllComments(username))
                _posts.postValue(fetchAllPosts(username))
                _uiState.postValue(UiState.Idle)
            }.onFailure {
                _uiState.postValue(UiState.Error(it.message ?: "Unknown error"))
            }
        }
    }

    private suspend fun fetchAllComments(username: String): List<RedditItem.Comment> {
        val result = mutableListOf<CommentData>()
        var after: String? = null
        do {
            val page = api.getComments(username, after = after)
            result.addAll(page.data.children.map { it.data })
            after = page.data.after
        } while (after != null)
        return result.map { RedditItem.Comment(it) }
    }

    private suspend fun fetchAllPosts(username: String): List<RedditItem.Post> {
        val result = mutableListOf<PostData>()
        var after: String? = null
        do {
            val page = api.getPosts(username, after = after)
            result.addAll(page.data.children.map { it.data })
            after = page.data.after
        } while (after != null)
        return result.map { RedditItem.Post(it) }
    }

    // ── Delete selected ───────────────────────────────────────────────────────

    fun deleteSelected() {
        val selectedComments = _comments.value.orEmpty().filter { it.selected }
        val selectedPosts    = _posts.value.orEmpty().filter { it.selected }
        val total            = selectedComments.size + selectedPosts.size
        if (total == 0) return

        _uiState.value = UiState.DeleteProgress(0, total)
        viewModelScope.launch {
            var done = 0
            runCatching {
                for (item in selectedComments) {
                    runCatching { api.editItem(item.data.name) }
                    api.deleteItem(item.data.name)
                    done++
                    _uiState.postValue(UiState.DeleteProgress(done, total))
                }
                for (item in selectedPosts) {
                    // Only self-posts can be edited; link posts can still be deleted
                    if (item.data.isSelf) runCatching { api.editItem(item.data.name) }
                    api.deleteItem(item.data.name)
                    done++
                    _uiState.postValue(UiState.DeleteProgress(done, total))
                }
                // Remove deleted items from lists
                _comments.postValue(_comments.value.orEmpty().filterNot { it.selected })
                _posts.postValue(_posts.value.orEmpty().filterNot { it.selected })
                _uiState.postValue(UiState.DeleteDone)
            }.onFailure {
                _uiState.postValue(UiState.Error("Delete failed: ${it.message}"))
            }
        }
    }

    // ── Selection helpers ─────────────────────────────────────────────────────

    fun selectAll(type: ItemType, selected: Boolean) {
        when (type) {
            ItemType.COMMENT -> _comments.value = _comments.value.orEmpty().map { it.copy(selected = selected) }
            ItemType.POST    -> _posts.value    = _posts.value.orEmpty().map { it.copy(selected = selected) }
        }
    }

    fun selectMatching(type: ItemType, maxScore: Int, minAgeDays: Long) {
        when (type) {
            ItemType.COMMENT -> _comments.value = _comments.value.orEmpty().map {
                it.copy(selected = it.score <= maxScore && it.ageDays >= minAgeDays)
            }
            ItemType.POST -> _posts.value = _posts.value.orEmpty().map {
                it.copy(selected = it.score <= maxScore && it.ageDays >= minAgeDays)
            }
        }
    }

    fun logout() {
        storage.clear()
    }

    enum class ItemType { COMMENT, POST }
}
