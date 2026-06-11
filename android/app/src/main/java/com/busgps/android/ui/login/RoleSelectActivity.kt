package com.busgps.android.ui.login

import android.content.Intent
import android.content.SharedPreferences
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.busgps.android.BuildConfig
import com.busgps.android.databinding.ActivityRoleSelectBinding
import com.busgps.android.network.ApiClient
import com.busgps.android.ui.admin.AdminActivity
import com.busgps.android.ui.driver.DriverActivity
import com.busgps.android.ui.parent.ParentDashboardActivity
import com.busgps.android.ui.superadmin.SuperAdminActivity
import com.busgps.android.util.LocaleHelper
import kotlinx.coroutines.launch

class RoleSelectActivity : AppCompatActivity() {

    private lateinit var binding: ActivityRoleSelectBinding
    private lateinit var prefs: SharedPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        ApiClient.init(applicationContext)

        prefs = getSharedPreferences("session", MODE_PRIVATE)
        binding = ActivityRoleSelectBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnLanguage.setOnClickListener {
            LocaleHelper.toggle()  // persists + recreates the activity stack
        }

        binding.btnParent.setOnClickListener {
            startActivity(Intent(this, ParentLoginActivity::class.java))
        }
        binding.btnDriver.setOnClickListener {
            startActivity(Intent(this, DriverLoginActivity::class.java))
        }
        binding.btnAdmin.setOnClickListener {
            startActivity(Intent(this, AdminLoginActivity::class.java))
        }

        binding.tvVersion.text = "v${BuildConfig.VERSION_NAME}"

        // Stay signed in: if we have a saved role AND the server session is still
        // valid, jump straight to the dashboard. Otherwise fall back to the chooser.
        val savedRole = prefs.getString("role", null)
        if (savedRole != null) verifySessionAndNavigate(savedRole)
    }

    private fun verifySessionAndNavigate(role: String) {
        lifecycleScope.launch {
            val live = try {
                ApiClient.api.getMe().body()?.role != null
            } catch (_: Exception) {
                // Network error on launch: trust the saved role rather than logging out.
                true
            }
            if (live) {
                navigateToRole(role)
            } else {
                // Session expired/invalid (e.g. server restarted): clear and show chooser.
                prefs.edit().clear().apply()
                ApiClient.clearSession()
            }
        }
    }

    private fun navigateToRole(role: String) {
        val intent = when (role) {
            "PARENT"      -> Intent(this, ParentDashboardActivity::class.java)
            "DRIVER"      -> Intent(this, DriverActivity::class.java)
            "SUPER_ADMIN" -> Intent(this, SuperAdminActivity::class.java)
            "SCHOOL_ADMIN" -> Intent(this, AdminActivity::class.java)
            else -> null
        }
        intent?.let {
            it.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            startActivity(it)
        }
    }
}
