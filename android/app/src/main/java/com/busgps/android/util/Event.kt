package com.busgps.android.util

/**
 * A LiveData payload meant to be consumed once (navigation, one-shot actions).
 * Prevents re-firing when an Activity re-subscribes after a configuration change.
 */
class Event<out T>(private val content: T) {
    private var handled = false

    /** Returns the content the first time, then null on subsequent calls. */
    fun getIfNotHandled(): T? =
        if (handled) null else { handled = true; content }
}
