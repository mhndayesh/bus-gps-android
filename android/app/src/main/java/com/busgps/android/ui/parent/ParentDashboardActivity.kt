package com.busgps.android.ui.parent

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.busgps.android.R
import com.busgps.android.databinding.ActivityParentDashboardBinding
import com.busgps.android.model.Kid
import com.busgps.android.network.ApiClient
import com.busgps.android.ui.adapters.KidAdapter
import com.busgps.android.ui.login.RoleSelectActivity
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.overlay.Marker

class ParentDashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityParentDashboardBinding
    private val vm: ParentViewModel by viewModels()
    private val busMarkers = mutableMapOf<Int, Marker>()

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
            binding.rvKids.adapter = KidAdapter(kids) { kid ->
                kid.busId?.let { vm.joinBusRoom(it) }
            }
            binding.tvNoKids.visibility = if (kids.isEmpty()) View.VISIBLE else View.GONE
        }

        vm.busLocation.observe(this) { update ->
            val point = GeoPoint(update.lat, update.lng)
            val marker = busMarkers.getOrPut(update.busId) {
                Marker(binding.mapView).also {
                    it.title = "Bus ${update.busId}"
                    it.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                    binding.mapView.overlays.add(it)
                }
            }
            marker.position = point
            binding.mapView.controller.animateTo(point)
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
