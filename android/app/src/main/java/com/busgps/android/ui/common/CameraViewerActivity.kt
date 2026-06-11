package com.busgps.android.ui.common

import android.graphics.BitmapFactory
import android.os.Bundle
import android.util.Base64
import androidx.appcompat.app.AppCompatActivity
import com.busgps.android.databinding.ActivityCameraViewerBinding
import com.busgps.android.network.ApiClient
import com.busgps.android.network.SocketManager
import org.json.JSONObject

/**
 * Live camera viewer for parents / admins. Joins the bus stream and renders
 * incoming `bus_camera_frame` events (base64 JPEG) into an ImageView.
 * Matches the web viewer contract in super_admin.html / parent dashboards.
 */
class CameraViewerActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_BUS_ID = "extra_bus_id"
        const val EXTRA_TITLE = "extra_title"
    }

    private lateinit var binding: ActivityCameraViewerBinding
    private var busId = -1

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityCameraViewerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        busId = intent.getIntExtra(EXTRA_BUS_ID, -1)
        if (busId < 0) { finish(); return }

        binding.btnClose.setOnClickListener { finish() }

        SocketManager.connect(ApiClient.getCookiesForSocket(), busId)
        SocketManager.joinBusStream(busId)

        SocketManager.on("bus_stream_status") { args ->
            try {
                val obj = args[0] as JSONObject
                if (obj.optInt("bus_id", -1) == busId && !obj.optBoolean("streaming", false)) {
                    runOnUiThread { binding.tvStatus.text = "Camera offline — waiting for driver…" }
                }
            } catch (_: Exception) {}
        }

        SocketManager.on("bus_camera_frame") { args ->
            try {
                val obj = args[0] as JSONObject
                if (obj.optInt("bus_id", -1) != busId) return@on
                val frame = obj.optString("frame", "")
                val b64 = frame.substringAfter("base64,", frame)
                val bytes = Base64.decode(b64, Base64.DEFAULT)
                val bmp = BitmapFactory.decodeByteArray(bytes, 0, bytes.size) ?: return@on
                runOnUiThread {
                    binding.imgFrame.setImageBitmap(bmp)
                    binding.tvStatus.text = "🔴 LIVE"
                }
            } catch (_: Exception) {}
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        SocketManager.off("bus_camera_frame")
        SocketManager.off("bus_stream_status")
    }
}
