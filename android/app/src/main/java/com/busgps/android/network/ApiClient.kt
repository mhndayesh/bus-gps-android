package com.busgps.android.network

import android.content.Context
import com.busgps.android.BuildConfig
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {

    private var cookieJar: PersistentCookieJar? = null
    private var csrfToken: String? = null

    private lateinit var retrofit: Retrofit
    lateinit var api: ApiService

    fun init(context: Context) {
        cookieJar = PersistentCookieJar(context)

        val logging = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BODY
                    else HttpLoggingInterceptor.Level.NONE
        }

        val client = OkHttpClient.Builder()
            .cookieJar(cookieJar!!)
            .followRedirects(false)  // handle login 302 manually
            .addInterceptor(logging)
            .addInterceptor { chain ->
                val original = chain.request()
                val method = original.method
                val req = if (method == "POST" || method == "PUT" || method == "DELETE") {
                    val token = csrfToken
                    if (token != null) {
                        original.newBuilder()
                            .header("X-CSRFToken", token)
                            .build()
                    } else original
                } else original
                chain.proceed(req)
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

    fun setCsrfToken(token: String) {
        csrfToken = token
    }

    fun clearSession() {
        cookieJar?.clear()
        csrfToken = null
    }

    fun getCookiesForSocket(): String {
        val url = okhttp3.HttpUrl.Builder()
            .scheme("https")
            .host(BuildConfig.BASE_URL.removePrefix("https://").removePrefix("http://").substringBefore("/"))
            .build()
        return cookieJar?.loadForRequest(url)
            ?.joinToString("; ") { "${it.name}=${it.value}" } ?: ""
    }
}
