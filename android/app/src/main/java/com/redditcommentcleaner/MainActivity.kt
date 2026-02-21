package com.redditcommentcleaner

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.redditcommentcleaner.auth.LoginActivity
import com.redditcommentcleaner.dashboard.DashboardActivity
import com.redditcommentcleaner.util.TokenStorage

/** Routes to Login or Dashboard depending on stored token. */
class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val next = if (TokenStorage(this).isLoggedIn()) {
            Intent(this, DashboardActivity::class.java)
        } else {
            Intent(this, LoginActivity::class.java)
        }
        startActivity(next)
        finish()
    }
}
