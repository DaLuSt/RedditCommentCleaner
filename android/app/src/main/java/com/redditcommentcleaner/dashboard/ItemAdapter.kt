package com.redditcommentcleaner.dashboard

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.redditcommentcleaner.databinding.ItemRedditRowBinding
import com.redditcommentcleaner.model.RedditItem

class ItemAdapter(
    private val onSelectionChanged: () -> Unit
) : ListAdapter<RedditItem, ItemAdapter.ViewHolder>(DiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemRedditRowBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    inner class ViewHolder(private val b: ItemRedditRowBinding) : RecyclerView.ViewHolder(b.root) {
        fun bind(item: RedditItem) {
            b.checkBox.isChecked = item.selected
            b.tvSubreddit.text   = "r/${item.subreddit}"
            b.tvScore.text       = "↑ ${item.score}"
            b.tvAge.text         = "${item.ageDays}d"

            when (item) {
                is RedditItem.Comment -> {
                    b.tvType.text    = "Comment"
                    b.tvContent.text = item.data.body.take(120)
                }
                is RedditItem.Post -> {
                    b.tvType.text    = "Post"
                    b.tvContent.text = item.data.title
                }
            }

            b.checkBox.setOnCheckedChangeListener(null)
            b.checkBox.setOnCheckedChangeListener { _, checked ->
                item.selected = checked
                onSelectionChanged()
            }
            b.root.setOnClickListener {
                item.selected = !item.selected
                b.checkBox.isChecked = item.selected
                onSelectionChanged()
            }
        }
    }

    private class DiffCallback : DiffUtil.ItemCallback<RedditItem>() {
        override fun areItemsTheSame(old: RedditItem, new: RedditItem) = old.name == new.name
        override fun areContentsTheSame(old: RedditItem, new: RedditItem) =
            old.name == new.name && old.selected == new.selected
    }
}
