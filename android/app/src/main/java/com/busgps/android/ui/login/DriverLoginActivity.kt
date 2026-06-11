package com.busgps.android.ui.login

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.busgps.android.R
import com.busgps.android.databinding.ActivityLoginBinding
import com.busgps.android.network.ApiClient
import com.busgps.android.repository.AuthRepository
import com.busgps.android.repository.AuthResult
import com.busgps.android.ui.driver.DriverActivity
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.launch

class DriverLoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private val repo = AuthRepository()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.tvRoleTitle.text = getString(R.string.driver_login_title)
        binding.tvRoleSubtitle.text = getString(R.string.driver_login_subtitle)

        binding.btnLogin.setOnClickListener {
            val username = binding.etUsername.text.toString().trim()
            val password = binding.etPassword.text.toString().trim()
            if (username.isEmpty() || password.isEmpty()) {
                Snackbar.make(binding.root, getString(R.string.enter_credentials), Snackbar.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            doLogin(username, password)
        }

        binding.tvBack.setOnClickListener { finish() }
    }

    private fun doLogin(username: String, password: String) {
        binding.btnLogin.isEnabled = false
        binding.progressBar.visibility = View.VISIBLE

        lifecycleScope.launch {
            when (val result = repo.driverLogin(username, password)) {
                is AuthResult.Success -> {
                    // Fetch bus info for this driver before navigating
                    var busId = -1
                    var plate = ""
                    try {
                        val info = ApiClient.api.getDriverInfo()
                        busId = info.body()?.busId ?: -1
                        plate = info.body()?.plate ?: ""
                    } catch (_: Exception) {}

                    getSharedPreferences("session", MODE_PRIVATE).edit()
                        .putString("role", "DRIVER")
                        .putInt("bus_id", busId)
                        .putString("bus_plate", plate)
                        .apply()

                    startActivity(Intent(this@DriverLoginActivity, DriverActivity::class.java).apply {
                        flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                    })
                }
                is AuthResult.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnLogin.isEnabled = true
                    Snackbar.make(binding.root, getString(result.msgRes), Snackbar.LENGTH_LONG).show()
                }
            }
        }
    }
}
