package com.busgps.android.network

import android.util.Log
import com.busgps.android.BuildConfig
import io.socket.client.IO
import io.socket.client.Socket
import org.json.JSONObject
import java.net.URI

object SocketManager {

    private const val TAG = "SocketManager"
    private var socket: Socket? = null

    fun connect(cookieHeader: String) {
        if (socket?.connected() == true) return

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
            on(Socket.EVENT_CONNECT) { Log.d(TAG, "Connected") }
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
            .put("speed", speed)
        socket?.emit("driver_gps_update", payload)
    }

    fun emitAttendance(studentId: String, status: String, busId: Int) {
        val payload = JSONObject()
            .put("student_id", studentId)
            .put("status", status)
            .put("bus_id", busId)
        socket?.emit("manual_attendance", payload)
    }

    fun on(event: String, callback: (Array<Any>) -> Unit) {
        socket?.on(event, callback)
    }

    fun off(event: String) {
        socket?.off(event)
    }

    fun disconnect() {
        socket?.disconnect()
        socket = null
    }

    val isConnected get() = socket?.connected() == true
}
