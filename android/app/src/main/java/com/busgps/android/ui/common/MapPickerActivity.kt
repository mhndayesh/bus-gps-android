package com.busgps.android.ui.common

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.busgps.android.databinding.ActivityMapPickerBinding
import com.google.android.gms.location.LocationServices
import org.osmdroid.events.MapEventsReceiver
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.MapEventsOverlay

/**
 * Reusable map location picker. Tap the map (or "Use my location") to drop a pin,
 * then Confirm. Returns the chosen lat/lng via Activity result extras.
 *
 * Launch with optional EXTRA_LAT / EXTRA_LNG to pre-place the marker (for editing).
 * On RESULT_OK, read RESULT_LAT / RESULT_LNG from the returned Intent.
 */
class MapPickerActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_LAT = "extra_lat"
        const val EXTRA_LNG = "extra_lng"
        const val EXTRA_TITLE = "extra_title"
        const val RESULT_LAT = "result_lat"
        const val RESULT_LNG = "result_lng"
    }

    private lateinit var binding: ActivityMapPickerBinding
    private var marker: Marker? = null
    private var picked: GeoPoint? = null

    private val locationPermission = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { grants ->
        if (grants[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
            grants[Manifest.permission.ACCESS_COARSE_LOCATION] == true) {
            goToMyLocation()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMapPickerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        intent.getStringExtra(EXTRA_TITLE)?.let { binding.tvTitle.text = it }

        binding.mapView.apply {
            setTileSource(TileSourceFactory.MAPNIK)
            setMultiTouchControls(true)
            controller.setZoom(15.0)
        }

        // Pre-place marker if editing an existing location, else center on Riyadh.
        val initLat = intent.getDoubleExtra(EXTRA_LAT, Double.NaN)
        val initLng = intent.getDoubleExtra(EXTRA_LNG, Double.NaN)
        if (!initLat.isNaN() && !initLng.isNaN()) {
            val p = GeoPoint(initLat, initLng)
            placeMarker(p)
            binding.mapView.controller.setCenter(p)
        } else {
            binding.mapView.controller.setCenter(GeoPoint(24.7136, 46.6753))
        }

        // Tap to place the pin.
        val receiver = object : MapEventsReceiver {
            override fun singleTapConfirmedHelper(p: GeoPoint): Boolean {
                placeMarker(p); return true
            }
            override fun longPressHelper(p: GeoPoint): Boolean { placeMarker(p); return true }
        }
        binding.mapView.overlays.add(MapEventsOverlay(receiver))

        binding.btnMyLocation.setOnClickListener { requestMyLocation() }
        binding.btnConfirm.setOnClickListener { confirm() }
    }

    private fun placeMarker(p: GeoPoint) {
        picked = p
        if (marker == null) {
            marker = Marker(binding.mapView).apply {
                setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                binding.mapView.overlays.add(this)
            }
        }
        marker!!.position = p
        binding.mapView.invalidate()
        binding.tvCoords.text = "Lat: %.5f, Lng: %.5f".format(p.latitude, p.longitude)
        binding.btnConfirm.isEnabled = true
    }

    private fun requestMyLocation() {
        val fine = Manifest.permission.ACCESS_FINE_LOCATION
        val coarse = Manifest.permission.ACCESS_COARSE_LOCATION
        if (ContextCompat.checkSelfPermission(this, fine) == PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(this, coarse) == PackageManager.PERMISSION_GRANTED) {
            goToMyLocation()
        } else {
            locationPermission.launch(arrayOf(fine, coarse))
        }
    }

    private fun goToMyLocation() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
            != PackageManager.PERMISSION_GRANTED &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION)
            != PackageManager.PERMISSION_GRANTED) return

        LocationServices.getFusedLocationProviderClient(this).lastLocation
            .addOnSuccessListener { loc ->
                if (loc != null) {
                    val p = GeoPoint(loc.latitude, loc.longitude)
                    placeMarker(p)
                    binding.mapView.controller.animateTo(p)
                }
            }
    }

    private fun confirm() {
        val p = picked ?: return
        setResult(RESULT_OK, Intent().apply {
            putExtra(RESULT_LAT, p.latitude)
            putExtra(RESULT_LNG, p.longitude)
        })
        finish()
    }

    override fun onResume() { super.onResume(); binding.mapView.onResume() }
    override fun onPause() { super.onPause(); binding.mapView.onPause() }
}
