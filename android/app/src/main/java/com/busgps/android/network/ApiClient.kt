package com.busgps.android.network

import android.content.Context
import com.busgps.android.BuildConfig
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.logging.HttpLoggingInterceptor
import org.json.JSONObject
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {

    private var cookieJar: PersistentCookieJar? = null
    @Volatile private var csrfToken: String? = null

    private lateinit var retrofit: Retrofit
    lateinit var api: ApiService

    fun init(context: Context) {
        cookieJar = PersistentCookieJar(context)

        // SECURITY: never log bodies (they contain passwords) and redact the
        // session cookie + CSRF token from header logs. HEADERS level only.
        val logging = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.HEADERS
                    else HttpLoggingInterceptor.Level.NONE
            redactHeader("Cookie")
            redactHeader("Set-Cookie")
            redactHeader("X-CSRFToken")
        }

        val client = OkHttpClient.Builder()
            .cookieJar(cookieJar!!)
            .followRedirects(false)  // handle login 302 manually
            .addInterceptor(logging)
            .addInterceptor { chain ->
                val original = chain.request()
                val method = original.method
                if (method == "POST" || method == "PUT" || method == "DELETE") {
                    var resp = chain.proceed(withCsrf(original))
                    // CSRF tokens expire (~1h). On a 400, refresh the token once and retry
                    // so saves don't silently fail mid-session.
                    if (resp.code == 400) {
                        resp.close()
                        if (refreshCsrfBlocking()) {
                            resp = chain.proceed(withCsrf(original))
                        }
                    }
                    resp
                } else {
                    chain.proceed(original)
                }
            }
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()

        retrofit = Retrofit.Builder()
            .baseUrl(BuildConfig.BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        api = retrofit.create(ApiService::class.java)
    }

    private fun withCsrf(original: Request): Request {
        val token = csrfToken ?: return original
        return original.newBuilder().header("X-CSRFToken", token).build()
    }

    /** Synchronous CSRF token fetch (safe to call from inside the interceptor;
     *  /api/csrf-token is a GET so it doesn't re-enter the CSRF logic). */
    private fun refreshCsrfBlocking(): Boolean {
        return try {
            val bare = OkHttpClient.Builder().cookieJar(cookieJar!!).build()
            val req = Request.Builder().url(BuildConfig.BASE_URL + "api/csrf-token").get().build()
            bare.newCall(req).execute().use { r ->
                val body = r.body?.string() ?: return false
                val token = JSONObject(body).optString("token", "")
                if (token.isNotEmpty()) { csrfToken = token; true } else false
            }
        } catch (_: Exception) {
            false
        }
    }

    fun setCsrfToken(token: String) {
        csrfToken = token
    }

    fun getCsrfToken(): String? = csrfToken

    fun clearSession() {
        cookieJar?.clear()
        csrfToken = null
    }

    fun getCookiesForSocket(): String {
        val scheme = if (BuildConfig.BASE_URL.startsWith("https")) "https" else "http"
        val hostAndPort = BuildConfig.BASE_URL.removePrefix("https://").removePrefix("http://").substringBefore("/")
        val host = hostAndPort.substringBefore(":")
        val portString = hostAndPort.substringAfter(":", "")

        val urlBuilder = okhttp3.HttpUrl.Builder()
            .scheme(scheme)
            .host(host)

        if (portString.isNotEmpty()) {
            try {
                urlBuilder.port(portString.toInt())
            } catch (_: Exception) {}
        }

        return cookieJar?.loadForRequest(urlBuilder.build())
            ?.joinToString("; ") { "${it.name}=${it.value}" } ?: ""
    }
}
