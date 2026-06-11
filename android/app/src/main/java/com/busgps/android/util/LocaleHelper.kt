package com.busgps.android.util

import androidx.appcompat.app.AppCompatDelegate
import androidx.core.os.LocaleListCompat

/**
 * App language switching. Uses AppCompat's per-app locale API, which (together
 * with the AppLocalesMetadataHolderService declared in the manifest with
 * autoStoreLocales=true) persists the choice and re-applies it on every launch.
 */
object LocaleHelper {

    fun isArabic(): Boolean =
        AppCompatDelegate.getApplicationLocales().toLanguageTags().startsWith("ar")

    fun setLanguage(langTag: String) {
        AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(langTag))
    }

    /** Flip between Arabic and English. */
    fun toggle() {
        setLanguage(if (isArabic()) "en" else "ar")
    }
}
