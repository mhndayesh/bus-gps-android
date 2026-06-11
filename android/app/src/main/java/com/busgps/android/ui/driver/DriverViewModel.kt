package com.busgps.android.ui.driver

import android.location.Location
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.busgps.android.model.ManifestItem
import com.busgps.android.model.RouteStop
import com.busgps.android.network.SocketManager
import com.busgps.android.repository.DataRepository
import com.busgps.android.util.Event
import kotlinx.coroutines.launch

class DriverViewModel : ViewModel() {

    private val repo = DataRepository()

    private val _manifest = MutableLiveData<List<ManifestItem>>()
    val manifest: LiveData<List<ManifestItem>> = _manifest

    private val _routeStops = MutableLiveData<List<RouteStop>>()
    val routeStops: LiveData<List<RouteStop>> = _routeStops

    private val _loading = MutableLiveData(false)
    val loading: LiveData<Boolean> = _loading

    private val _statusMsg = MutableLiveData<String>()
    val statusMsg: LiveData<String> = _statusMsg

    private val _tripActive = MutableLiveData(false)
    val tripActive: LiveData<Boolean> = _tripActive

    // One-shot event: stops to launch Google Maps navigation with. Wrapped in
    // Event so it fires exactly once and does NOT replay on rotation.
    private val _openNav = MutableLiveData<Event<List<RouteStop>>>()
    val openNav: LiveData<Event<List<RouteStop>>> = _openNav

    var busId: Int = -1
    private var lastLocation: Location? = null

    val lastLat: Double? get() = lastLocation?.latitude
    val lastLng: Double? get() = lastLocation?.longitude

    fun connectSocket(cookie: String) {
        SocketManager.connect(cookie, busId)
    }

    fun loadManifest() {
        _loading.value = true
        viewModelScope.launch {
            _manifest.value = repo.getManifest()
            _loading.value = false
        }
    }

    /** Count of students not yet BOARDED (used to warn before starting a trip). */
    fun notBoardedCount(): Int =
        _manifest.value?.count { it.status != "BOARDED" } ?: 0

    fun startTrip() {
        _tripActive.value = true
        // Fetch the optimized route, then signal the UI to open Google Maps.
        viewModelScope.launch {
            val stops = repo.optimizeRoute(busId, lastLocation?.latitude, lastLocation?.longitude)
            _routeStops.value = stops
            _openNav.value = Event(stops)
        }
    }

    fun endTrip() {
        _tripActive.value = false
        loadManifest()
    }

    fun sendGpsUpdate(location: Location) {
        lastLocation = location
        if (busId < 0) return
        // Match the website: only broadcast GPS while a trip is active.
        if (_tripActive.value == true) {
            SocketManager.emitGpsUpdate(busId, location.latitude, location.longitude, location.speed)
        }
    }

    fun markBoarded(studentId: String) {
        if (busId < 0) return
        SocketManager.emitAttendance(studentId, "BOARDED", busId)
        updateLocalStatus(studentId, "BOARDED")
        _statusMsg.value = "Marked as BOARDED"
    }

    fun markDropped(studentId: String) {
        if (busId < 0) return
        SocketManager.emitAttendance(studentId, "DROPPED", busId)
        updateLocalStatus(studentId, "DROPPED")
        _statusMsg.value = "Marked as DROPPED"
    }

    private fun updateLocalStatus(studentId: String, status: String) {
        val current = _manifest.value?.toMutableList() ?: return
        val idx = current.indexOfFirst { it.id == studentId }
        if (idx >= 0) {
            current[idx] = current[idx].copy(status = status)
            _manifest.postValue(current)
        }
    }

    fun optimizeRoute() {
        if (busId < 0) return
        _loading.value = true
        val loc = lastLocation
        viewModelScope.launch {
            _routeStops.value = repo.optimizeRoute(busId, loc?.latitude, loc?.longitude)
            _loading.value = false
        }
    }

    override fun onCleared() {
        super.onCleared()
        SocketManager.disconnect()
    }
}
