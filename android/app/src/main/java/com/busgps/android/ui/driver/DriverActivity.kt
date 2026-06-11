package com.busgps.android.ui.driver

import android.Manifest
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.os.Looper
import android.view.View
import androidx.activity.addCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.LinearLayoutManager
import com.busgps.android.databinding.ActivityDriverBinding
import com.busgps.android.model.RouteStop
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
    private val manifestAdapter by lazy {
        ManifestAdapter(onBoard = { vm.markBoarded(it) }, onDrop = { vm.markDropped(it) })
    }

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
        if (grants[Manifest.permission.ACCESS_FINE_LOCATION] != true &&
            grants[Manifest.permission.ACCESS_COARSE_LOCATION] != true) {
            Snackbar.make(binding.root, "Location permission required to start a trip", Snackbar.LENGTH_LONG).show()
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

        binding.btnTrip.setOnClickListener { onTripButton() }
        binding.btnOptimize.setOnClickListener { vm.optimizeRoute() }
        binding.btnCamera.setOnClickListener {
            if (vm.busId < 0) {
                Snackbar.make(binding.root, "No bus assigned — ask your admin", Snackbar.LENGTH_LONG).show()
            } else {
                startActivity(Intent(this, CameraStreamActivity::class.java)
                    .putExtra(CameraStreamActivity.EXTRA_BUS_ID, vm.busId))
            }
        }
        binding.swipeRefresh.setOnRefreshListener { vm.loadManifest() }
        binding.btnLogout.setOnClickListener { logout() }
        binding.btnBack.setOnClickListener { logout() }
        onBackPressedDispatcher.addCallback(this) { logout() }
    }

    // ── Trip lifecycle (mirrors the website's idle → in-trip → stop flow) ──

    private fun onTripButton() {
        if (vm.tripActive.value == true) {
            vm.endTrip()
            return
        }
        if (vm.busId < 0) {
            Snackbar.make(binding.root, "No bus assigned — ask your admin", Snackbar.LENGTH_LONG).show()
            return
        }
        // Ensure we have location permission before starting GPS tracking.
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
            != PackageManager.PERMISSION_GRANTED) {
            locationPermission.launch(arrayOf(
                Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION))
            Snackbar.make(binding.root, "Grant location, then press Start Trip", Snackbar.LENGTH_LONG).show()
            return
        }
        // Warn if some students aren't boarded yet (same as the website modal).
        val missing = vm.notBoardedCount()
        if (missing > 0) {
            AlertDialog.Builder(this)
                .setTitle("$missing student(s) not boarded")
                .setMessage("Some students haven't been marked as boarded. Start the trip anyway?")
                .setPositiveButton("Start anyway") { _, _ -> beginTrip() }
                .setNegativeButton("Recheck") { _, _ -> vm.loadManifest() }
                .show()
        } else {
            beginTrip()
        }
    }

    private fun beginTrip() {
        startLocationUpdates()
        vm.startTrip()  // optimizes route, then emits openNav to launch Google Maps
        Snackbar.make(binding.root, "Trip started — sharing live location", Snackbar.LENGTH_SHORT).show()
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
        binding.rvManifest.adapter = manifestAdapter
    }

    private fun observeViewModel() {
        vm.loading.observe(this) { loading ->
            binding.swipeRefresh.isRefreshing = loading
            binding.progressBar.visibility = if (loading) View.VISIBLE else View.GONE
        }

        vm.manifest.observe(this) { manifest ->
            manifestAdapter.submit(manifest)
            val plate = getSharedPreferences("session", MODE_PRIVATE).getString("bus_plate", "") ?: ""
            val prefix = if (plate.isNotEmpty()) "Bus $plate" else "Driver"
            binding.tvStudentCount.text = "$prefix | ${manifest.size} students"
        }

        vm.routeStops.observe(this) { stops ->
            // Remove route markers but keep the driver's own-location marker.
            binding.mapView.overlays.removeAll { it is Marker && it !== selfMarker }
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

        vm.tripActive.observe(this) { active ->
            if (active) {
                binding.btnTrip.text = "■  End Trip"
                binding.btnTrip.setBackgroundColor(0xFFE53935.toInt())
            } else {
                binding.btnTrip.text = "▶  Start Trip"
                binding.btnTrip.setBackgroundColor(ContextCompat.getColor(this, com.busgps.android.R.color.role_driver))
                fusedLocation.removeLocationUpdates(locationCallback)
            }
        }

        // One-shot: open Google Maps navigation when a trip starts (does not
        // replay on rotation thanks to the Event wrapper).
        vm.openNav.observe(this) { event ->
            event.getIfNotHandled()?.let { stops -> openGoogleMapsNavigation(stops) }
        }
    }

    /**
     * Launch Google Maps turn-by-turn navigation through the optimized stops.
     * Origin defaults to the driver's current location; the last stop is the
     * destination and the rest become ordered waypoints.
     */
    private fun openGoogleMapsNavigation(stops: List<RouteStop>) {
        if (stops.isEmpty()) {
            Snackbar.make(binding.root, "No boarded students with a location to navigate to", Snackbar.LENGTH_LONG).show()
            return
        }
        // Google Maps supports up to ~9 waypoints via URL.
        val capped = stops.take(10)
        val destination = capped.last()
        val waypoints = capped.dropLast(1)

        val sb = StringBuilder("https://www.google.com/maps/dir/?api=1")
        vm.lastLat?.let { la -> vm.lastLng?.let { ln -> sb.append("&origin=$la,$ln") } }
        sb.append("&destination=${destination.lat},${destination.lng}")
        if (waypoints.isNotEmpty()) {
            val wp = waypoints.joinToString("|") { "${it.lat},${it.lng}" }
            sb.append("&waypoints=").append(Uri.encode(wp))
        }
        sb.append("&travelmode=driving")

        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(sb.toString()))
        // Prefer the Google Maps app if installed; otherwise any maps/browser handler.
        intent.setPackage("com.google.android.apps.maps")
        if (intent.resolveActivity(packageManager) != null) {
            startActivity(intent)
        } else {
            val fallback = Intent(Intent.ACTION_VIEW, Uri.parse(sb.toString()))
            if (fallback.resolveActivity(packageManager) != null) startActivity(fallback)
            else Snackbar.make(binding.root, "No maps app available", Snackbar.LENGTH_LONG).show()
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

    override fun onResume() {
        super.onResume()
        binding.mapView.onResume()
        // Resume GPS only if a trip is in progress.
        if (vm.tripActive.value == true) startLocationUpdates()
    }

    override fun onPause() {
        super.onPause()
        binding.mapView.onPause()
        // Stop GPS when not in the foreground to save battery / avoid hidden-map work.
        fusedLocation.removeLocationUpdates(locationCallback)
    }

    override fun onDestroy() {
        super.onDestroy()
        fusedLocation.removeLocationUpdates(locationCallback)
        binding.mapView.onDetach()
    }
}
