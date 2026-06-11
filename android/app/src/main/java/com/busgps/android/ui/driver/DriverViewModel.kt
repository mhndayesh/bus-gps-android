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

    var busId: Int = -1
    private var lastLocation: Location? = null

    fun connectSocket(cookie: String) {
        SocketManager.connect(cookie)
    }

    fun loadManifest() {
        _loading.value = true
        viewModelScope.launch {
            _manifest.value = repo.getManifest()
            _loading.value = false
        }
    }

    fun sendGpsUpdate(location: Location) {
        lastLocation = location
        if (busId < 0) return
        SocketManager.emitGpsUpdate(busId, location.latitude, location.longitude, location.speed)
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
