package com.busgps.android

import android.app.Application
import android.preference.PreferenceManager
import com.busgps.android.network.ApiClient
import org.osmdroid.config.Configuration

class App : Application() {
    override fun onCreate() {
        super.onCreate()
        ApiClient.init(this)
        Configuration.getInstance().load(this, PreferenceManager.getDefaultSharedPreferences(this))
        Configuration.getInstance().userAgentValue = packageName
    }
}
