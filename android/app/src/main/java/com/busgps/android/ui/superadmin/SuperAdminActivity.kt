package com.busgps.android.ui.superadmin

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.busgps.android.databinding.ActivitySuperAdminBinding
import com.busgps.android.network.ApiClient
import com.busgps.android.repository.DataRepository
import com.busgps.android.ui.login.RoleSelectActivity
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.launch

class SuperAdminActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySuperAdminBinding
    private val repo = DataRepository()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySuperAdminBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.rvSchools.layoutManager = LinearLayoutManager(this)
        loadSchools()

        binding.swipeRefresh.setOnRefreshListener { loadSchools() }
        binding.btnLogout.setOnClickListener { logout() }
    }

    private fun loadSchools() {
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            val schools = repo.getSchools()
            binding.progressBar.visibility = View.GONE
            binding.swipeRefresh.isRefreshing = false
            binding.tvSchoolCount.text = "${schools.size} schools"
            binding.rvSchools.adapter = SchoolAdapter(schools)
        }
    }

    private fun logout() {
        getSharedPreferences("session", MODE_PRIVATE).edit().clear().apply()
        ApiClient.clearSession()
        startActivity(Intent(this, RoleSelectActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        })
    }
}
