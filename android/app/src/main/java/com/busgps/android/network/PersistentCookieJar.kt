package com.busgps.android.network

import android.content.Context
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl

class PersistentCookieJar(context: Context) : CookieJar {

    private val prefs = context.getSharedPreferences("cookies", Context.MODE_PRIVATE)
    private val cache = mutableMapOf<String, MutableList<Cookie>>()

    init {
        prefs.all.forEach { (key, value) ->
            // stored as "host" → semicolon-separated cookie strings
            if (value is String) {
                cache[key] = value.split(";").mapNotNull { parseCookie(it, key) }.toMutableList()
            }
        }
    }

    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        val host = url.host
        val existing = cache.getOrPut(host) { mutableListOf() }
        cookies.forEach { new ->
            existing.removeAll { it.name == new.name }
            existing.add(new)
        }
        persist(host, existing)
    }

    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        return cache[url.host]?.filter { it.expiresAt > System.currentTimeMillis() } ?: emptyList()
    }

    fun clear() {
        cache.clear()
        prefs.edit().clear().apply()
    }

    private fun parseCookie(raw: String, host: String): Cookie? {
        return try {
            val parts = raw.split("=", limit = 2)
            if (parts.size != 2) return null
            Cookie.Builder()
                .name(parts[0].trim())
                .value(parts[1].trim())
                .domain(host)
                .build()
        } catch (e: Exception) {
            null
        }
    }

    private fun persist(host: String, cookies: List<Cookie>) {
        val value = cookies.joinToString(";") { "${it.name}=${it.value}" }
        prefs.edit().putString(host, value).apply()
    }
}
