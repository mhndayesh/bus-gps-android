package com.busgps.android.network

import android.content.Context
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl
import org.json.JSONArray
import org.json.JSONObject

/**
 * Cookie jar that persists cookies to SharedPreferences while preserving their
 * full attributes (path, secure, httpOnly, hostOnly, persistent), and uses
 * OkHttp's own `Cookie.matches(url)` for retrieval — so a Secure session cookie
 * isn't silently downgraded or mismatched after an app restart.
 */
class PersistentCookieJar(context: Context) : CookieJar {

    private val prefs = context.getSharedPreferences("cookies", Context.MODE_PRIVATE)
    private val cache = mutableMapOf<String, MutableList<Cookie>>()

    init {
        prefs.all.forEach { (host, value) ->
            if (value is String) {
                cache[host] = deserialize(value).toMutableList()
            }
        }
    }

    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        val host = url.host
        val existing = cache.getOrPut(host) { mutableListOf() }
        cookies.forEach { new ->
            existing.removeAll { it.name == new.name && it.path == new.path }
            existing.add(new)
        }
        persist(host, existing)
    }

    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        val now = System.currentTimeMillis()
        val list = cache[url.host] ?: return emptyList()
        // Drop expired cookies and honor path/secure/domain matching.
        val valid = list.filter { it.expiresAt > now && it.matches(url) }
        if (valid.size != list.size) {
            cache[url.host] = list.filter { it.expiresAt > now }.toMutableList()
            persist(url.host, cache[url.host]!!)
        }
        return valid
    }

    fun clear() {
        cache.clear()
        prefs.edit().clear().apply()
    }

    private fun persist(host: String, cookies: List<Cookie>) {
        val arr = JSONArray()
        cookies.forEach { c ->
            arr.put(JSONObject().apply {
                put("name", c.name)
                put("value", c.value)
                put("domain", c.domain)
                put("path", c.path)
                put("expiresAt", c.expiresAt)
                put("secure", c.secure)
                put("httpOnly", c.httpOnly)
                put("hostOnly", c.hostOnly)
            })
        }
        prefs.edit().putString(host, arr.toString()).apply()
    }

    private fun deserialize(stored: String): List<Cookie> {
        return try {
            val arr = JSONArray(stored)
            (0 until arr.length()).mapNotNull { i ->
                val o = arr.getJSONObject(i)
                val b = Cookie.Builder()
                    .name(o.getString("name"))
                    .value(o.getString("value"))
                    .path(o.optString("path", "/"))
                    .expiresAt(o.optLong("expiresAt", Long.MAX_VALUE))
                if (o.optBoolean("hostOnly", true)) b.hostOnlyDomain(o.getString("domain"))
                else b.domain(o.getString("domain"))
                if (o.optBoolean("secure", false)) b.secure()
                if (o.optBoolean("httpOnly", false)) b.httpOnly()
                try { b.build() } catch (_: Exception) { null }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }
}
