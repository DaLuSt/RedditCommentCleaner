package com.redditcommentcleaner.dashboard

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.google.android.material.tabs.TabLayout
import com.redditcommentcleaner.auth.LoginActivity
import com.redditcommentcleaner.databinding.ActivityDashboardBinding
import com.redditcommentcleaner.model.RedditItem

class DashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDashboardBinding
    private lateinit var commentAdapter: ItemAdapter
    private lateinit var postAdapter: ItemAdapter

    private val vm: DashboardViewModel by viewModels {
        object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(cls: Class<T>) =
                DashboardViewModel(applicationContext) as T
        }
    }

    private val currentType get() =
        if (binding.tabLayout.selectedTabPosition == 0) DashboardViewModel.ItemType.COMMENT
        else DashboardViewModel.ItemType.POST

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupRecyclerViews()
        setupTabs()
        setupButtons()
        observeViewModel()

        vm.loadAll()
    }

    // ── Setup ────────────────────────────────────────────────────────────────

    private fun setupRecyclerViews() {
        commentAdapter = ItemAdapter { updateDeleteButtonLabel() }
        postAdapter    = ItemAdapter { updateDeleteButtonLabel() }
        binding.rvComments.adapter = commentAdapter
        binding.rvPosts.adapter    = postAdapter
    }

    private fun setupTabs() {
        binding.tabLayout.addOnTabSelectedListener(object : TabLayout.OnTabSelectedListener {
            override fun onTabSelected(tab: TabLayout.Tab) {
                binding.rvComments.visibility = if (tab.position == 0) View.VISIBLE else View.GONE
                binding.rvPosts.visibility    = if (tab.position == 1) View.VISIBLE else View.GONE
                updateDeleteButtonLabel()
            }
            override fun onTabUnselected(tab: TabLayout.Tab?) = Unit
            override fun onTabReselected(tab: TabLayout.Tab?) = Unit
        })
    }

    private fun setupButtons() {
        binding.btnLoad.setOnClickListener { vm.loadAll() }

        binding.btnSelectAll.setOnClickListener  { vm.selectAll(currentType, true) }
        binding.btnSelectNone.setOnClickListener { vm.selectAll(currentType, false) }

        binding.btnSelectMatching.setOnClickListener {
            val maxScore  = binding.etMaxScore.text.toString().toIntOrNull()  ?: 0
            val minAgeDays= binding.etMinAge.text.toString().toLongOrNull()   ?: 0L
            vm.selectMatching(currentType, maxScore, minAgeDays)
        }

        binding.btnDelete.setOnClickListener { confirmDelete() }

        binding.btnLogout.setOnClickListener {
            vm.logout()
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
        }
    }

    // ── Observe ──────────────────────────────────────────────────────────────

    private fun observeViewModel() {
        vm.comments.observe(this) { items ->
            commentAdapter.submitList(items.toList())
            binding.tabLayout.getTabAt(0)?.text = "Comments (${items.size})"
            updateDeleteButtonLabel()
        }
        vm.posts.observe(this) { items ->
            postAdapter.submitList(items.toList())
            binding.tabLayout.getTabAt(1)?.text = "Posts (${items.size})"
            updateDeleteButtonLabel()
        }
        vm.uiState.observe(this) { state ->
            when (state) {
                is UiState.Loading -> showLoading(true)
                is UiState.Idle    -> showLoading(false)
                is UiState.Error   -> { showLoading(false); toast(state.message) }
                is UiState.DeleteProgress -> {
                    binding.progressBar.visibility = View.VISIBLE
                    binding.progressBar.progress   = (state.done * 100 / state.total.coerceAtLeast(1))
                    binding.tvStatus.text = "Deleting ${state.done}/${state.total}…"
                }
                is UiState.DeleteDone -> {
                    binding.progressBar.visibility = View.GONE
                    binding.tvStatus.text          = ""
                    toast("Done!")
                }
            }
        }
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    private fun updateDeleteButtonLabel() {
        val count = when (currentType) {
            DashboardViewModel.ItemType.COMMENT ->
                vm.comments.value.orEmpty().count { it.selected }
            DashboardViewModel.ItemType.POST    ->
                vm.posts.value.orEmpty().count { it.selected }
        }
        binding.btnDelete.text = if (count > 0) "Delete Selected ($count)" else "Delete Selected"
        binding.btnDelete.isEnabled = count > 0
    }

    private fun showLoading(loading: Boolean) {
        binding.progressBar.visibility = if (loading) View.VISIBLE else View.GONE
        binding.tvStatus.text          = if (loading) "Loading…" else ""
    }

    private fun confirmDelete() {
        val commentCount = vm.comments.value.orEmpty().count { it.selected }
        val postCount    = vm.posts.value.orEmpty().count { it.selected }
        val total        = commentCount + postCount
        if (total == 0) return

        AlertDialog.Builder(this)
            .setTitle("Confirm Deletion")
            .setMessage(
                buildString {
                    append("You are about to permanently delete:\n")
                    if (commentCount > 0) append("  • $commentCount comment(s)\n")
                    if (postCount    > 0) append("  • $postCount post(s)\n")
                    append("\nThis cannot be undone.")
                }
            )
            .setPositiveButton("Delete") { _, _ -> vm.deleteSelected() }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun toast(msg: String) = Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
}
