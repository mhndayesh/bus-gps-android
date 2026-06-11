package com.busgps.android.network

import android.util.Log
import com.busgps.android.BuildConfig
import io.socket.client.IO
import io.socket.client.Socket
import org.json.JSONObject
import java.net.URI

object SocketManager {

    private const val TAG = "SocketManager"
    @Volatile private var socket: Socket? = null

    @Synchronized
    fun connect(cookieHeader: String, joinBusId: Int = -1) {
        if (socket?.connected() == true) {
            if (joinBusId >= 0) joinRoom(joinBusId)
            return
        }

        val options = IO.Options.builder()
            .setExtraHeaders(
                mapOf("Cookie" to listOf(cookieHeader))
            )
            .setTransports(arrayOf("websocket"))
            .setReconnection(true)
            .setReconnectionAttempts(10)
            .setReconnectionDelay(1000)
            .build()

        socket = IO.socket(URI.create(BuildConfig.BASE_URL), options).apply {
            on(Socket.EVENT_CONNECT) {
                Log.d(TAG, "Connected")
                if (joinBusId >= 0) joinRoom(joinBusId)
            }
            on(Socket.EVENT_DISCONNECT) { Log.d(TAG, "Disconnected") }
            on(Socket.EVENT_CONNECT_ERROR) { args -> Log.e(TAG, "Error: ${args[0]}") }
            connect()
        }
    }

    fun joinRoom(busId: Int) {
        val payload = JSONObject().put("room", busId)
        socket?.emit("join", payload)
    }

    fun emitGpsUpdate(busId: Int, lat: Double, lng: Double, speed: Float) {
        val payload = JSONObject()
            .put("bus_id", busId)
            .put("lat", lat)
            .put("lng", lng)
            .put("speed", speed * 3.6) // convert m/s to km/h
        socket?.emit("driver_gps_update", payload)
    }

    fun emitAttendance(studentId: String, status: String, busId: Int) {
        val payload = JSONObject()
            .put("student_id", studentId)
            .put("status", status)
            .put("bus_id", busId)
        socket?.emit("manual_attendance", payload)
    }

    // --- Camera streaming ---

    fun emitCameraStart(busId: Int) {
        socket?.emit("camera_stream_start", JSONObject().put("bus_id", busId))
    }

    fun emitCameraStop(busId: Int) {
        socket?.emit("camera_stream_stop", JSONObject().put("bus_id", busId))
    }

    fun emitCameraFrame(busId: Int, dataUrl: String) {
        socket?.emit("camera_frame", JSONObject().put("bus_id", busId).put("frame", dataUrl))
    }

    fun joinBusStream(busId: Int) {
        socket?.emit("join_bus_stream", JSONObject().put("bus_id", busId))
    }

    @Synchronized
    fun on(event: String, callback: (Array<Any>) -> Unit) {
        // Replace any previous handler for this event so re-registering on
        // onResume/refresh doesn't stack duplicate listeners.
        socket?.off(event)
        socket?.on(event, callback)
    }

    @Synchronized
    fun off(event: String) {
        socket?.off(event)
    }

    @Synchronized
    fun disconnect() {
        socket?.off()
        socket?.disconnect()
        socket = null
    }

    val isConnected get() = socket?.connected() == true
}
