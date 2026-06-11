package com.busgps.android.ui.driver

import com.busgps.android.R
import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Matrix
import android.graphics.Rect
import android.graphics.YuvImage
import android.os.Bundle
import android.util.Base64
import android.util.Log
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import com.busgps.android.databinding.ActivityCameraStreamBinding
import com.busgps.android.network.ApiClient
import com.busgps.android.network.SocketManager
import java.io.ByteArrayOutputStream
import java.util.concurrent.Executors

/**
 * Driver camera streaming. Captures frames via CameraX ImageAnalysis, JPEG-encodes
 * them and emits `camera_frame` over Socket.IO at a throttled rate, matching the
 * web driver_app.html contract (camera_stream_start / camera_frame / camera_stream_stop).
 */
class CameraStreamActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_BUS_ID = "extra_bus_id"
        private const val TAG = "CameraStream"
        private const val FRAME_INTERVAL_MS = 150L  // ~6–7 fps
        private const val JPEG_QUALITY = 50
    }

    private lateinit var binding: ActivityCameraStreamBinding
    private val analysisExecutor = Executors.newSingleThreadExecutor()
    private var cameraProvider: ProcessCameraProvider? = null
    private var lensFacing = CameraSelector.LENS_FACING_BACK
    private var busId = -1
    private var lastSentAt = 0L
    private var streaming = false

    private val cameraPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) startCamera()
        else { binding.tvStatus.text = getString(R.string.camera_permission_denied); finishAfterShortDelay() }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityCameraStreamBinding.inflate(layoutInflater)
        setContentView(binding.root)

        busId = intent.getIntExtra(EXTRA_BUS_ID, -1)
        if (busId < 0) { finish(); return }

        // Ensure the socket is connected with our session cookie.
        SocketManager.connect(ApiClient.getCookiesForSocket(), busId)

        binding.btnStop.setOnClickListener { finish() }
        binding.btnFlip.setOnClickListener {
            lensFacing = if (lensFacing == CameraSelector.LENS_FACING_BACK)
                CameraSelector.LENS_FACING_FRONT else CameraSelector.LENS_FACING_BACK
            startCamera()
        }

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            cameraPermission.launch(Manifest.permission.CAMERA)
        }
    }

    private fun startCamera() {
        val future = ProcessCameraProvider.getInstance(this)
        future.addListener({
            try {
                cameraProvider = future.get()
                bindUseCases()
            } catch (e: Exception) {
                Log.e(TAG, "Camera init failed", e)
                binding.tvStatus.text = getString(R.string.camera_unavailable)
            }
        }, ContextCompat.getMainExecutor(this))
    }

    private fun bindUseCases() {
        val provider = cameraProvider ?: return
        provider.unbindAll()

        val preview = Preview.Builder().build().also {
            it.setSurfaceProvider(binding.previewView.surfaceProvider)
        }

        val analysis = ImageAnalysis.Builder()
            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
            .build()
            .also { it.setAnalyzer(analysisExecutor, ::analyzeFrame) }

        val selector = CameraSelector.Builder().requireLensFacing(lensFacing).build()

        try {
            provider.bindToLifecycle(this, selector, preview, analysis)
            if (!streaming) {
                SocketManager.emitCameraStart(busId)
                streaming = true
            }
        } catch (e: Exception) {
            Log.e(TAG, "bindToLifecycle failed", e)
            binding.tvStatus.text = getString(R.string.camera_unavailable)
        }
    }

    private fun analyzeFrame(image: ImageProxy) {
        val now = System.currentTimeMillis()
        if (now - lastSentAt < FRAME_INTERVAL_MS) { image.close(); return }
        lastSentAt = now
        try {
            val jpeg = image.toJpeg(JPEG_QUALITY, image.imageInfo.rotationDegrees)
            if (jpeg != null) {
                val b64 = Base64.encodeToString(jpeg, Base64.NO_WRAP)
                SocketManager.emitCameraFrame(busId, "data:image/jpeg;base64,$b64")
            }
        } catch (e: Exception) {
            Log.e(TAG, "frame encode failed", e)
        } finally {
            image.close()
        }
    }

    /** Convert a YUV_420_888 ImageProxy to a rotation-corrected JPEG byte array. */
    private fun ImageProxy.toJpeg(quality: Int, rotationDegrees: Int): ByteArray? {
        if (format != ImageFormat.YUV_420_888) return null
        val nv21 = yuv420ToNv21(this)
        val yuv = YuvImage(nv21, ImageFormat.NV21, width, height, null)
        val out = ByteArrayOutputStream()
        yuv.compressToJpeg(Rect(0, 0, width, height), quality, out)
        var bytes = out.toByteArray()
        if (rotationDegrees != 0) {
            val bmp = BitmapFactory.decodeByteArray(bytes, 0, bytes.size) ?: return bytes
            val m = Matrix().apply { postRotate(rotationDegrees.toFloat()) }
            val rotated = Bitmap.createBitmap(bmp, 0, 0, bmp.width, bmp.height, m, true)
            val out2 = ByteArrayOutputStream()
            rotated.compress(Bitmap.CompressFormat.JPEG, quality, out2)
            bytes = out2.toByteArray()
            bmp.recycle(); rotated.recycle()
        }
        return bytes
    }

    private fun yuv420ToNv21(image: ImageProxy): ByteArray {
        val w = image.width; val h = image.height
        val ySize = w * h
        val nv21 = ByteArray(ySize + ySize / 2)
        val yPlane = image.planes[0].buffer
        val uPlane = image.planes[1].buffer
        val vPlane = image.planes[2].buffer

        // Y
        val yRowStride = image.planes[0].rowStride
        if (yRowStride == w) {
            yPlane.get(nv21, 0, ySize)
        } else {
            var pos = 0
            for (row in 0 until h) {
                yPlane.position(row * yRowStride)
                yPlane.get(nv21, pos, w); pos += w
            }
        }

        // VU interleaved (NV21 = Y + VUVU...)
        val uvRowStride = image.planes[1].rowStride
        val uvPixelStride = image.planes[1].pixelStride
        var uvPos = ySize
        for (row in 0 until h / 2) {
            for (col in 0 until w / 2) {
                val vuIndex = row * uvRowStride + col * uvPixelStride
                vPlane.position(vuIndex); nv21[uvPos++] = vPlane.get()
                uPlane.position(vuIndex); nv21[uvPos++] = uPlane.get()
            }
        }
        return nv21
    }

    private fun finishAfterShortDelay() {
        binding.root.postDelayed({ finish() }, 1500)
    }

    override fun onDestroy() {
        super.onDestroy()
        if (streaming) {
            SocketManager.emitCameraStop(busId)
            streaming = false
        }
        cameraProvider?.unbindAll()
        analysisExecutor.shutdown()
    }
}
