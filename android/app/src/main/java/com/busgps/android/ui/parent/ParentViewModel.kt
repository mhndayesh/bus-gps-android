package com.busgps.android.ui.parent

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.busgps.android.model.BusLocationUpdate
import com.busgps.android.model.Kid
import com.busgps.android.model.StudentStatusUpdate
import com.busgps.android.network.SocketManager
import com.busgps.android.repository.DataRepository
import com.google.gson.Gson
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import org.json.JSONObject

class ParentViewModel : ViewModel() {

    private val repo = DataRepository()
    private val gson = Gson()

    private val _kids = MutableLiveData<List<Kid>>()
    val kids: LiveData<List<Kid>> = _kids

    private val _busLocation = MutableLiveData<BusLocationUpdate>()
    val busLocation: LiveData<BusLocationUpdate> = _busLocation

    private val _loading = MutableLiveData<Boolean>()
    val loading: LiveData<Boolean> = _loading

    private var pollingJob: Job? = null

    fun loadKids() {
        _loading.value = true
        viewModelScope.launch {
            _kids.value = repo.getMyKids()
            _loading.value = false
        }
    }

    /**
     * Poll the children list every 10s, matching the website. This is required
     * because NFC boarding/dropping is written to the DB by listener.py, which
     * emits no socket event — so the socket alone would miss those updates.
     */
    fun startPolling() {
        if (pollingJob?.isActive == true) return
        pollingJob = viewModelScope.launch {
            while (isActive) {
                delay(10_000)
                try { _kids.value = repo.getMyKids() } catch (_: Exception) {}
            }
        }
    }

    fun stopPolling() {
        pollingJob?.cancel()
        pollingJob = null
    }

    fun setupSocket(cookieHeader: String) {
        SocketManager.connect(cookieHeader)

        SocketManager.on("update_map") { args ->
            try {
                val obj = args[0] as JSONObject
                val update = BusLocationUpdate(
                    busId = obj.getInt("bus_id"),
                    lat = obj.getDouble("lat"),
                    lng = obj.getDouble("lng"),
                    speed = obj.getDouble("speed")
                )
                _busLocation.postValue(update)
            } catch (_: Exception) {}
        }

        SocketManager.on("student_status_update") { args ->
            try {
                val obj = args[0] as JSONObject
                val studentId = obj.getString("student_id")
                val status = obj.getString("status")
                val current = _kids.value?.toMutableList() ?: return@on
                val idx = current.indexOfFirst { it.id == studentId }
                if (idx >= 0) {
                    current[idx] = current[idx].copy(onBus = status == "BOARDED")
                    _kids.postValue(current)
                }
            } catch (_: Exception) {}
        }
    }

    fun joinBusRoom(busId: Int) {
        SocketManager.joinRoom(busId)
    }

    override fun onCleared() {
        super.onCleared()
        SocketManager.off("update_map")
        SocketManager.off("student_status_update")
    }
}
