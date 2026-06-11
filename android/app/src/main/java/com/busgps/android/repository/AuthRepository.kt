package com.busgps.android.repository

import com.busgps.android.network.ApiClient

sealed class AuthResult {
    object Success : AuthResult()
    data class Error(val message: String) : AuthResult()
}

class AuthRepository {

    suspend fun fetchCsrfToken(): Boolean {
        return try {
            val resp = ApiClient.api.getCsrfToken()
            val token = resp.body()?.csrfToken
            if (token != null) {
                ApiClient.setCsrfToken(token)
                true
            } else false
        } catch (e: Exception) {
            false
        }
    }

    suspend fun adminLogin(username: String, password: String): AuthResult {
        return login(username, password, role = "ADMIN")
    }

    suspend fun driverLogin(username: String, password: String): AuthResult {
        return login(username, password, role = "DRIVER")
    }

    suspend fun parentLogin(username: String, password: String): AuthResult {
        return login(username, password, role = "PARENT")
    }

    private suspend fun login(username: String, password: String, role: String): AuthResult {
        return try {
            if (!fetchCsrfToken()) return AuthResult.Error("Could not reach server")
            val token = ApiClient.api.getCsrfToken().body()?.csrfToken ?: ""
            val resp = when (role) {
                "ADMIN"  -> ApiClient.api.adminLogin(username, password, token)
                "DRIVER" -> ApiClient.api.driverLogin(username, password, token)
                else     -> ApiClient.api.parentLogin(username, password, token)
            }
            when {
                resp.code() == 302 -> AuthResult.Success  // Flask redirect = success
                resp.code() == 401 -> AuthResult.Error("Invalid username or password")
                resp.code() == 403 -> AuthResult.Error("Access denied for this role")
                else -> AuthResult.Error("Login failed (${resp.code()})")
            }
        } catch (e: Exception) {
            AuthResult.Error(e.message ?: "Network error")
        }
    }

    suspend fun logout() {
        try { ApiClient.api.logout() } catch (_: Exception) {}
        ApiClient.clearSession()
    }
}
