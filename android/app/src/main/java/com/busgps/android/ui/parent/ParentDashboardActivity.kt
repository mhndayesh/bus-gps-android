package com.busgps.android.ui.parent

import android.app.AlertDialog
import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.activity.addCallback
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.busgps.android.R
import com.busgps.android.databinding.ActivityParentDashboardBinding
import com.busgps.android.model.Kid
import com.busgps.android.network.ApiClient
import com.busgps.android.ui.adapters.KidAdapter
import com.busgps.android.ui.common.CameraViewerActivity
import com.busgps.android.ui.login.RoleSelectActivity
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.overlay.Marker

class ParentDashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityParentDashboardBinding
    private val vm: ParentViewModel by viewModels()
    private val busMarkers = mutableMapOf<Int, Marker>()
    private var selectedBusId: Int? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityParentDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupMap()
        setupRecycler()
        observeViewModel()

        val cookie = ApiClient.getCookiesForSocket()
        vm.setupSocket(cookie)
        vm.loadKids()

        binding.swipeRefresh.setOnRefreshListener { vm.loadKids() }

        binding.btnLogout.setOnClickListener { logout() }
        binding.btnBack.setOnClickListener { logout() }
        onBackPressedDispatcher.addCallback(this) { logout() }
    }

    private fun setupMap() {
        binding.mapView.apply {
            setTileSource(TileSourceFactory.MAPNIK)
            setMultiTouchControls(true)
            controller.setZoom(13.0)
            controller.setCenter(GeoPoint(24.7136, 46.6753)) // Riyadh default
        }
    }

    private fun setupRecycler() {
        binding.rvKids.layoutManager = LinearLayoutManager(this)
    }

    private fun observeViewModel() {
        vm.loading.observe(this) { loading ->
            binding.swipeRefresh.isRefreshing = loading
        }

        vm.kids.observe(this) { kids ->
            // Auto-join socket rooms for all kids' buses so we receive updates
            kids.mapNotNull { it.busId }.distinct().forEach { busId ->
                vm.joinBusRoom(busId)
            }
            // Set default selected bus to the first kid's bus
            if (selectedBusId == null) {
                selectedBusId = kids.firstOrNull { it.busId != null }?.busId
            }
            binding.rvKids.adapter = KidAdapter(kids) { kid ->
                kid.busId?.let { busId ->
                    AlertDialog.Builder(this)
                        .setTitle(kid.name)
                        .setItems(arrayOf("Track on map", "📹 Watch camera")) { _, which ->
                            selectedBusId = busId
                            vm.joinBusRoom(busId)
                            if (which == 1) {
                                startActivity(
                                    Intent(this, CameraViewerActivity::class.java)
                                        .putExtra(CameraViewerActivity.EXTRA_BUS_ID, busId)
                                        .putExtra(CameraViewerActivity.EXTRA_TITLE, kid.name)
                                )
                            }
                        }
                        .show()
                }
            }
            binding.tvNoKids.visibility = if (kids.isEmpty()) View.VISIBLE else View.GONE
        }

        vm.busLocation.observe(this) { update ->
            val point = GeoPoint(update.lat, update.lng)
            // Look up plate from kids list
            val plate = vm.kids.value?.firstOrNull { it.busId == update.busId }?.busPlate
            val markerTitle = if (!plate.isNullOrEmpty()) "Bus $plate" else "Bus ${update.busId}"
            val marker = busMarkers.getOrPut(update.busId) {
                Marker(binding.mapView).also {
                    it.title = markerTitle
                    it.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                    binding.mapView.overlays.add(it)
                }
            }
            marker.title = markerTitle
            marker.position = point
            if (update.busId == selectedBusId) {
                binding.mapView.controller.animateTo(point)
            }
            binding.mapView.invalidate()
        }
    }

    private fun logout() {
        getSharedPreferences("session", MODE_PRIVATE).edit().clear().apply()
        ApiClient.clearSession()
        startActivity(Intent(this, RoleSelectActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        })
    }

    override fun onResume() {
        super.onResume()
        binding.mapView.onResume()
    }

    override fun onPause() {
        super.onPause()
        binding.mapView.onPause()
    }
}
