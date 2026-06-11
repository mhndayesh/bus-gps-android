package com.busgps.android.ui.admin

import android.app.AlertDialog
import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.ArrayAdapter
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import androidx.activity.addCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.busgps.android.R
import com.busgps.android.databinding.ActivityAdminBinding
import com.busgps.android.model.Bus
import com.busgps.android.model.Parent
import com.busgps.android.model.Student
import com.busgps.android.network.ApiClient
import com.busgps.android.ui.adapters.StudentAdapter
import com.busgps.android.ui.common.MapPickerActivity
import com.busgps.android.ui.login.RoleSelectActivity
import com.google.android.material.snackbar.Snackbar
import com.google.android.material.tabs.TabLayout

class AdminActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAdminBinding
    private val vm: AdminViewModel by viewModels()

    private var currentParents: List<Parent> = emptyList()
    private var currentBuses: List<Bus> = emptyList()

    // Student whose location is being set via the map picker.
    private var locationTargetStudentId: String? = null

    private val mapPicker = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == RESULT_OK) {
            val lat = result.data?.getDoubleExtra(MapPickerActivity.RESULT_LAT, Double.NaN) ?: return@registerForActivityResult
            val lng = result.data?.getDoubleExtra(MapPickerActivity.RESULT_LNG, Double.NaN) ?: return@registerForActivityResult
            val id = locationTargetStudentId
            if (!lat.isNaN() && !lng.isNaN() && id != null) {
                vm.updateStudentLocation(id, lat, lng)
            }
            locationTargetStudentId = null
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAdminBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupTabs()
        setupRecycler()
        observeViewModel()

        vm.loadAll()

        binding.swipeRefresh.setOnRefreshListener { vm.loadAll() }
        binding.fabAdd.setOnClickListener { showAddDialogForCurrentTab() }
        binding.btnLogout.setOnClickListener { logout() }
        binding.btnBack.setOnClickListener { logout() }
        onBackPressedDispatcher.addCallback(this) { logout() }
    }

    private fun setupTabs() {
        listOf("Overview", "Students", "Buses", "Drivers", "Parents").forEach { title ->
            binding.tabLayout.addTab(binding.tabLayout.newTab().setText(title))
        }
        binding.tabLayout.addOnTabSelectedListener(object : TabLayout.OnTabSelectedListener {
            override fun onTabSelected(tab: TabLayout.Tab) = showTab(tab.position)
            override fun onTabUnselected(tab: TabLayout.Tab) {}
            override fun onTabReselected(tab: TabLayout.Tab) {}
        })
    }

    private fun setupRecycler() {
        binding.rvItems.layoutManager = LinearLayoutManager(this)
    }

    private fun showTab(position: Int) {
        binding.statsCard.visibility = if (position == 0) View.VISIBLE else View.GONE
        binding.rvItems.visibility = if (position > 0) View.VISIBLE else View.GONE

        when (position) {
            1 -> showStudents()
            2 -> showBuses()
            3 -> showDrivers()
            4 -> showParents()
        }
    }

    private fun showStudents() {
        val students = vm.students.value ?: return
        binding.rvItems.adapter = StudentAdapter(students,
            onDelete = { vm.deleteStudent(it) },
            onAssignBus = { studentId -> showAssignBusDialog(studentId) },
            onSetLocation = { student -> openLocationPicker(student) }
        )
    }

    private fun openLocationPicker(student: Student) {
        locationTargetStudentId = student.id
        val intent = Intent(this, MapPickerActivity::class.java).apply {
            putExtra(MapPickerActivity.EXTRA_TITLE, "Set ${student.name}'s home")
            if (student.lat != null && student.lng != null) {
                putExtra(MapPickerActivity.EXTRA_LAT, student.lat)
                putExtra(MapPickerActivity.EXTRA_LNG, student.lng)
            }
        }
        mapPicker.launch(intent)
    }

    private fun showBuses() {
        val buses = vm.buses.value ?: return
        binding.rvItems.adapter = BusAdapter(buses,
            onAssignDriver = { busId -> showAssignDriverDialog(busId) }
        )
    }

    private fun showDrivers() {
        val drivers = vm.drivers.value ?: return
        binding.rvItems.adapter = DriverListAdapter(drivers)
    }

    private fun showParents() {
        val parents = vm.parents.value ?: return
        binding.rvItems.adapter = ParentListAdapter(parents)
    }

    private fun observeViewModel() {
        vm.loading.observe(this) { binding.swipeRefresh.isRefreshing = it }

        vm.stats.observe(this) { s ->
            binding.tvTotalBuses.text = "${s.totalBuses}"
            binding.tvActiveBuses.text = "${s.activeBuses}"
            binding.tvTotalStudents.text = "${s.totalStudents}"
            binding.tvPresent.text = "${s.presentStudents}"
        }

        vm.students.observe(this) {
            if (binding.tabLayout.selectedTabPosition == 1) showStudents()
        }
        vm.buses.observe(this) {
            currentBuses = it
            if (binding.tabLayout.selectedTabPosition == 2) showBuses()
        }
        vm.drivers.observe(this) {
            if (binding.tabLayout.selectedTabPosition == 3) showDrivers()
        }
        vm.parents.observe(this) {
            currentParents = it
            if (binding.tabLayout.selectedTabPosition == 4) showParents()
        }

        vm.toast.observe(this) {
            Snackbar.make(binding.root, it, Snackbar.LENGTH_SHORT).show()
        }
    }

    private fun showAddDialogForCurrentTab() {
        when (binding.tabLayout.selectedTabPosition) {
            1 -> showAddStudentDialog()
            3 -> showAddDriverDialog()
            4 -> showAddParentDialog()
            else -> {}
        }
    }

    private fun showAddStudentDialog() {
        // Guard: a student must be linked to a parent. If none exist, guide the admin.
        if (currentParents.isEmpty()) {
            AlertDialog.Builder(this)
                .setTitle("No parents yet")
                .setMessage("You must create a parent before adding a student. Open the Parents tab and add one first.")
                .setPositiveButton("Go to Parents") { _, _ ->
                    binding.tabLayout.getTabAt(4)?.select()
                }
                .setNegativeButton("Cancel", null)
                .show()
            return
        }

        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(48, 24, 48, 0) }

        val etName = EditText(this).apply { hint = "Student name" }

        val lblParent = TextView(this).apply {
            text = "Parent"
            setPadding(0, 24, 0, 4)
        }
        val spinnerParent = Spinner(this).apply {
            adapter = ArrayAdapter(this@AdminActivity, android.R.layout.simple_spinner_item,
                currentParents.map { it.name }).also { it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
        }

        val etNfc = EditText(this).apply { hint = "NFC tag ID (optional)" }

        layout.addView(etName)
        layout.addView(lblParent)
        layout.addView(spinnerParent)
        layout.addView(etNfc)

        AlertDialog.Builder(this)
            .setTitle("Add Student")
            .setMessage("Set the home location afterward with the 📍 button on the student row.")
            .setView(layout)
            .setPositiveButton("Add") { _, _ ->
                val name = etName.text.toString().trim()
                val parentId = currentParents.getOrNull(spinnerParent.selectedItemPosition)?.id
                    ?: return@setPositiveButton
                val nfc = etNfc.text.toString().trim()
                if (name.isNotEmpty()) vm.addStudent(name, parentId, nfcId = nfc)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showAddDriverDialog() {
        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(48, 16, 48, 0) }
        val etUser = EditText(this).apply { hint = "Username" }
        val etPass = EditText(this).apply { hint = "Password"; inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD }
        layout.addView(etUser); layout.addView(etPass)

        AlertDialog.Builder(this)
            .setTitle("Add Driver")
            .setView(layout)
            .setPositiveButton("Create") { _, _ ->
                val u = etUser.text.toString().trim()
                val p = etPass.text.toString().trim()
                if (u.isNotEmpty() && p.isNotEmpty()) vm.createDriver(u, p)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showAddParentDialog() {
        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(48, 16, 48, 0) }
        val etName = EditText(this).apply { hint = "Full name" }
        val etUser = EditText(this).apply { hint = "Username" }
        val etPass = EditText(this).apply { hint = "Password"; inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD }
        layout.addView(etName); layout.addView(etUser); layout.addView(etPass)

        AlertDialog.Builder(this)
            .setTitle("Add Parent")
            .setView(layout)
            .setPositiveButton("Create") { _, _ ->
                val n = etName.text.toString().trim()
                val u = etUser.text.toString().trim()
                val p = etPass.text.toString().trim()
                if (n.isNotEmpty() && u.isNotEmpty() && p.isNotEmpty()) vm.createParent(n, u, p)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showAssignBusDialog(studentId: String) {
        val buses = currentBuses
        AlertDialog.Builder(this)
            .setTitle("Assign to Bus")
            .setItems(buses.map { it.plate }.toTypedArray()) { _, i ->
                vm.assignBus(studentId, buses[i].id)
            }
            .show()
    }

    private fun showAssignDriverDialog(busId: String) {
        val drivers = vm.drivers.value ?: return
        AlertDialog.Builder(this)
            .setTitle("Assign Driver")
            .setItems(drivers.map { it.name }.toTypedArray()) { _, i ->
                vm.assignDriver(drivers[i].id, busId)
            }
            .show()
    }

    private fun logout() {
        getSharedPreferences("session", MODE_PRIVATE).edit().clear().apply()
        ApiClient.clearSession()
        startActivity(Intent(this, RoleSelectActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        })
    }
}
