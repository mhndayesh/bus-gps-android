package com.busgps.android.ui.driver

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.Looper
import android.view.View
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.LinearLayoutManager
import com.busgps.android.databinding.ActivityDriverBinding
import com.busgps.android.network.ApiClient
import com.busgps.android.ui.adapters.ManifestAdapter
import com.busgps.android.ui.login.RoleSelectActivity
import com.google.android.gms.location.*
import com.google.android.material.snackbar.Snackbar
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.overlay.Marker

class DriverActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDriverBinding
    private val vm: DriverViewModel by viewModels()
    private lateinit var fusedLocation: FusedLocationProviderClient
    private var selfMarker: Marker? = null

    private val locationRequest = LocationRequest.Builder(
        Priority.PRIORITY_HIGH_ACCURACY, 2000L
    ).setMinUpdateIntervalMillis(1000).build()

    private val locationCallback = object : LocationCallback() {
        override fun onLocationResult(result: LocationResult) {
            result.lastLocation?.let { loc ->
                vm.sendGpsUpdate(loc)
                updateSelfOnMap(loc.latitude, loc.longitude)
            }
        }
    }

    private val locationPermission = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { grants ->
        if (grants[Manifest.permission.ACCESS_FINE_LOCATION] == true) {
            startLocationUpdates()
        } else {
            Snackbar.make(binding.root, "Location permission required for GPS tracking", Snackbar.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDriverBinding.inflate(layoutInflater)
        setContentView(binding.root)

        fusedLocation = LocationServices.getFusedLocationProviderClient(this)

        val prefs = getSharedPreferences("session", MODE_PRIVATE)
        vm.busId = prefs.getInt("bus_id", -1)
        val plate = prefs.getString("bus_plate", "") ?: ""

        setupMap()
        setupRecycler()
        observeViewModel()

        binding.tvStudentCount.text = if (plate.isNotEmpty()) "Bus $plate" else "Driver Dashboard"

        val cookie = ApiClient.getCookiesForSocket()
        vm.connectSocket(cookie)  // joins bus room on connect
        vm.loadManifest()

        binding.btnOptimize.setOnClickListener { vm.optimizeRoute() }
        binding.swipeRefresh.setOnRefreshListener { vm.loadManifest() }
        binding.btnLogout.setOnClickListener { logout() }

        checkAndRequestLocation()
    }

    private fun setupMap() {
        binding.mapView.apply {
            setTileSource(TileSourceFactory.MAPNIK)
            setMultiTouchControls(true)
            controller.setZoom(15.0)
        }
    }

    private fun setupRecycler() {
        binding.rvManifest.layoutManager = LinearLayoutManager(this)
    }

    private fun observeViewModel() {
        vm.loading.observe(this) { loading ->
            binding.swipeRefresh.isRefreshing = loading
            binding.progressBar.visibility = if (loading) View.VISIBLE else View.GONE
        }

        vm.manifest.observe(this) { manifest ->
            binding.rvManifest.adapter = ManifestAdapter(manifest,
                onBoard = { vm.markBoarded(it) },
                onDrop  = { vm.markDropped(it) }
            )
            val plate = getSharedPreferences("session", MODE_PRIVATE).getString("bus_plate", "") ?: ""
            val prefix = if (plate.isNotEmpty()) "Bus $plate" else "Driver"
            binding.tvStudentCount.text = "$prefix | ${manifest.size} students"
        }

        vm.routeStops.observe(this) { stops ->
            binding.mapView.overlays.removeAll { it is Marker }
            stops.forEachIndexed { i, stop ->
                Marker(binding.mapView).apply {
                    position = GeoPoint(stop.lat, stop.lng)
                    title = "${i + 1}. ${stop.name}"
                    setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                    binding.mapView.overlays.add(this)
                }
            }
            if (stops.isNotEmpty()) {
                binding.mapView.controller.animateTo(GeoPoint(stops[0].lat, stops[0].lng))
            }
            binding.mapView.invalidate()
        }

        vm.statusMsg.observe(this) { msg ->
            Snackbar.make(binding.root, msg, Snackbar.LENGTH_SHORT).show()
        }
    }

    private fun updateSelfOnMap(lat: Double, lng: Double) {
        val point = GeoPoint(lat, lng)
        if (selfMarker == null) {
            selfMarker = Marker(binding.mapView).apply {
                title = "My Location"
                setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_CENTER)
                binding.mapView.overlays.add(this)
            }
        }
        selfMarker!!.position = point
        binding.mapView.controller.animateTo(point)
        binding.mapView.invalidate()
    }

    private fun checkAndRequestLocation() {
        val fine = Manifest.permission.ACCESS_FINE_LOCATION
        val coarse = Manifest.permission.ACCESS_COARSE_LOCATION
        if (ContextCompat.checkSelfPermission(this, fine) == PackageManager.PERMISSION_GRANTED) {
            startLocationUpdates()
        } else {
            locationPermission.launch(arrayOf(fine, coarse))
        }
    }

    private fun startLocationUpdates() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
            == PackageManager.PERMISSION_GRANTED) {
            fusedLocation.requestLocationUpdates(locationRequest, locationCallback, Looper.getMainLooper())
        }
    }

    private fun logout() {
        fusedLocation.removeLocationUpdates(locationCallback)
        getSharedPreferences("session", MODE_PRIVATE).edit().clear().apply()
        ApiClient.clearSession()
        startActivity(Intent(this, RoleSelectActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        })
    }

    override fun onResume() { super.onResume(); binding.mapView.onResume() }
    override fun onPause() { super.onPause(); binding.mapView.onPause() }

    override fun onDestroy() {
        super.onDestroy()
        fusedLocation.removeLocationUpdates(locationCallback)
    }
}
