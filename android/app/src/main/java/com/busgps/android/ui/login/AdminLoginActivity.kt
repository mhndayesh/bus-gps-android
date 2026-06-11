package com.busgps.android.ui.login

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.busgps.android.databinding.ActivityLoginBinding
import com.busgps.android.network.ApiClient
import com.busgps.android.repository.AuthRepository
import com.busgps.android.repository.AuthResult
import com.busgps.android.ui.admin.AdminActivity
import com.busgps.android.ui.superadmin.SuperAdminActivity
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.launch

class AdminLoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private val repo = AuthRepository()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.tvRoleTitle.text = "School Admin Login"
        binding.tvRoleSubtitle.text = "Manage students, buses & drivers"

        binding.btnLogin.setOnClickListener {
            val username = binding.etUsername.text.toString().trim()
            val password = binding.etPassword.text.toString().trim()
            if (username.isEmpty() || password.isEmpty()) {
                Snackbar.make(binding.root, "Enter username and password", Snackbar.LENGTH_SHORT).show()
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
            when (val result = repo.adminLogin(username, password)) {
                is AuthResult.Success -> {
                    val role = try {
                        ApiClient.api.getMe().body()?.role ?: "SCHOOL_ADMIN"
                    } catch (_: Exception) { "SCHOOL_ADMIN" }

                    getSharedPreferences("session", MODE_PRIVATE).edit()
                        .putString("role", role)
                        .apply()

                    val dest = if (role == "SUPER_ADMIN") SuperAdminActivity::class.java
                               else AdminActivity::class.java
                    val intent = Intent(this@AdminLoginActivity, dest)
                    intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                    startActivity(intent)
                }
                is AuthResult.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnLogin.isEnabled = true
                    Snackbar.make(binding.root, result.message, Snackbar.LENGTH_LONG).show()
                }
            }
        }
    }
}
