package com.busgps.android.ui.login

import android.content.Intent
import android.content.SharedPreferences
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.busgps.android.BuildConfig
import com.busgps.android.databinding.ActivityRoleSelectBinding
import com.busgps.android.network.ApiClient
import com.busgps.android.ui.admin.AdminActivity
import com.busgps.android.ui.driver.DriverActivity
import com.busgps.android.ui.parent.ParentDashboardActivity

class RoleSelectActivity : AppCompatActivity() {

    private lateinit var binding: ActivityRoleSelectBinding
    private lateinit var prefs: SharedPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        ApiClient.init(applicationContext)

        prefs = getSharedPreferences("session", MODE_PRIVATE)
        binding = ActivityRoleSelectBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Auto-login if a saved role exists
        val savedRole = prefs.getString("role", null)
        if (savedRole != null) {
            navigateToRole(savedRole)
            return
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
    }

    private fun navigateToRole(role: String) {
        val intent = when (role) {
            "PARENT"      -> Intent(this, ParentDashboardActivity::class.java)
            "DRIVER"      -> Intent(this, DriverActivity::class.java)
            "SCHOOL_ADMIN", "SUPER_ADMIN" -> Intent(this, AdminActivity::class.java)
            else -> null
        }
        intent?.let {
            it.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            startActivity(it)
        }
    }

    override fun onResume() {
        super.onResume()
        // Clear saved role if user returned here (logged out)
        val savedRole = prefs.getString("role", null)
        if (savedRole != null) navigateToRole(savedRole)
    }
}
