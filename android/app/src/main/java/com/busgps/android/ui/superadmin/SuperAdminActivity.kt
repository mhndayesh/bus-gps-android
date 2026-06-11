package com.busgps.android.ui.superadmin

import android.app.AlertDialog
import android.content.Intent
import android.os.Bundle
import android.text.InputType
import android.view.View
import android.widget.ArrayAdapter
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import androidx.activity.addCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.busgps.android.R
import com.busgps.android.databinding.ActivitySuperAdminBinding
import com.busgps.android.model.Bus
import com.busgps.android.model.Driver
import com.busgps.android.model.Parent
import com.busgps.android.model.School
import com.busgps.android.model.Student
import com.busgps.android.network.ApiClient
import com.busgps.android.repository.DataRepository
import com.busgps.android.ui.adapters.StudentAdapter
import com.busgps.android.ui.admin.DriverListAdapter
import com.busgps.android.ui.common.CameraViewerActivity
import com.busgps.android.ui.common.MapPickerActivity
import com.busgps.android.ui.login.RoleSelectActivity
import com.google.android.material.snackbar.Snackbar
import com.google.android.material.tabs.TabLayout
import kotlinx.coroutines.launch

class SuperAdminActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySuperAdminBinding
    private val repo = DataRepository()

    private var schools: List<School> = emptyList()
    private var students: List<Student> = emptyList()
    private var buses: List<Bus> = emptyList()
    private var drivers: List<Driver> = emptyList()
    private var parents: List<Parent> = emptyList()

    private var locationTargetStudentId: String? = null

    private val mapPicker = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == RESULT_OK) {
            val lat = result.data?.getDoubleExtra(MapPickerActivity.RESULT_LAT, Double.NaN) ?: return@registerForActivityResult
            val lng = result.data?.getDoubleExtra(MapPickerActivity.RESULT_LNG, Double.NaN) ?: return@registerForActivityResult
            val id = locationTargetStudentId
            if (!lat.isNaN() && !lng.isNaN() && id != null) {
                doAction { repo.updateStudentLocation(id, lat, lng, "") }
            }
            locationTargetStudentId = null
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySuperAdminBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.rvItems.layoutManager = LinearLayoutManager(this)

        setupTabs()
        loadAll()

        binding.swipeRefresh.setOnRefreshListener { loadAll() }
        binding.fabAdd.setOnClickListener { showAddForCurrentTab() }
        binding.btnLogout.setOnClickListener { logout() }
        binding.btnLang.setOnClickListener { com.busgps.android.util.LocaleHelper.toggle() }
        binding.btnBack.setOnClickListener { logout() }
        onBackPressedDispatcher.addCallback(this) { logout() }
    }

    private fun setupTabs() {
        listOf(getString(R.string.overview), getString(R.string.schools), getString(R.string.students), getString(R.string.buses), getString(R.string.drivers), getString(R.string.parents)).forEach {
            binding.tabLayout.addTab(binding.tabLayout.newTab().setText(it))
        }
        binding.tabLayout.addOnTabSelectedListener(object : TabLayout.OnTabSelectedListener {
            override fun onTabSelected(tab: TabLayout.Tab) = showTab(tab.position)
            override fun onTabUnselected(tab: TabLayout.Tab) {}
            override fun onTabReselected(tab: TabLayout.Tab) {}
        })
    }

    private fun showTab(pos: Int) {
        binding.statsCard.visibility = if (pos == 0) View.VISIBLE else View.GONE
        binding.rvItems.visibility = if (pos > 0) View.VISIBLE else View.GONE
        when (pos) {
            1 -> showSchools()
            2 -> showStudents()
            3 -> showBuses()
            4 -> showDrivers()
            5 -> showParents()
        }
    }

    private fun loadAll() {
        binding.swipeRefresh.isRefreshing = true
        lifecycleScope.launch {
            try {
                repo.refreshCsrf()  // keep a valid CSRF token so saves persist
                schools = repo.getSchools()
                students = repo.getStudents()
                buses = repo.getBuses()
                drivers = repo.getDrivers()
                parents = repo.getParents()
                repo.getDashboardStats()?.let { s ->
                    binding.tvTotalBuses.text = "${s.totalBuses}"
                    binding.tvActiveBuses.text = "${s.activeBuses}"
                    binding.tvTotalStudents.text = "${s.totalStudents}"
                    binding.tvPresent.text = "${s.presentStudents}"
                }
            } finally {
                binding.swipeRefresh.isRefreshing = false
                showTab(binding.tabLayout.selectedTabPosition)
            }
        }
    }

    // --- Tab renderers ---

    private fun showSchools() {
        binding.rvItems.adapter = SchoolAdapter(schools)
    }

    private fun showStudents() {
        binding.rvItems.adapter = StudentAdapter(
            students,
            onDelete = { id ->
                confirm(getString(R.string.delete_student_q)) {
                    doAction { repo.deleteStudent(id) }
                }
            },
            onAssignBus = { id -> showAssignBusDialog(id) },
            onSetLocation = { student -> openLocationPicker(student) }
        )
    }

    private fun openLocationPicker(student: Student) {
        locationTargetStudentId = student.id
        val intent = Intent(this, MapPickerActivity::class.java).apply {
            putExtra(MapPickerActivity.EXTRA_TITLE, getString(R.string.set_home_of, student.name))
            if (student.lat != null && student.lng != null) {
                putExtra(MapPickerActivity.EXTRA_LAT, student.lat)
                putExtra(MapPickerActivity.EXTRA_LNG, student.lng)
            }
        }
        mapPicker.launch(intent)
    }

    private fun showBuses() {
        binding.rvItems.adapter = SuperBusAdapter(
            buses,
            onAssignDriver = { busId -> showAssignDriverDialog(busId) },
            onDelete = { busId ->
                val plate = buses.find { it.id == busId }?.plate ?: busId
                confirm(getString(R.string.delete_bus_q, plate)) {
                    doAction { repo.deleteBus(busId) }
                }
            },
            onWatchCamera = { bus -> watchCamera(bus) }
        )
    }

    private fun watchCamera(bus: Bus) {
        val busIdInt = bus.id.toIntOrNull()
        if (busIdInt == null) { toast("Invalid bus id"); return }
        startActivity(
            Intent(this, CameraViewerActivity::class.java)
                .putExtra(CameraViewerActivity.EXTRA_BUS_ID, busIdInt)
                .putExtra(CameraViewerActivity.EXTRA_TITLE, bus.plate)
        )
    }

    private fun showDrivers() {
        binding.rvItems.adapter = DriverListAdapter(drivers)
    }

    private fun showParents() {
        binding.rvItems.adapter = SuperParentAdapter(
            parents,
            onEditCreds = { parent -> showEditParentCredsDialog(parent) }
        )
    }

    // --- FAB dispatch ---

    private fun showAddForCurrentTab() {
        when (binding.tabLayout.selectedTabPosition) {
            1 -> showCreateSchoolDialog()
            2 -> showAddStudentDialog()
            3 -> showAddBusDialog()
            4 -> showCreateDriverDialog()
            5 -> showCreateParentDialog()
        }
    }

    // --- Dialogs ---

    private fun showCreateSchoolDialog() {
        val layout = vstack {
            addEditText(getString(R.string.school_name_hint))
            addEditText(getString(R.string.admin_username_hint))
            addEditTextPassword(getString(R.string.admin_password_hint))
        }
        val schoolName = layout.getChildAt(0) as EditText
        val username = layout.getChildAt(1) as EditText
        val password = layout.getChildAt(2) as EditText

        AlertDialog.Builder(this)
            .setTitle(getString(R.string.create_school_admin))
            .setView(layout)
            .setPositiveButton(getString(R.string.create)) { _, _ ->
                val sn = schoolName.text.toString().trim()
                val u = username.text.toString().trim()
                val p = password.text.toString().trim()
                if (sn.isNotEmpty() && u.isNotEmpty() && p.isNotEmpty()) {
                    doAction { repo.createSchoolAdmin(sn, u, p) }
                }
            }
            .setNegativeButton(getString(R.string.cancel), null)
            .show()
    }

    private fun showAddStudentDialog() {
        if (parents.isEmpty()) {
            AlertDialog.Builder(this)
                .setTitle(getString(R.string.no_parents_title))
                .setMessage(getString(R.string.no_parents_msg))
                .setPositiveButton(getString(R.string.go_to_parents)) { _, _ -> binding.tabLayout.getTabAt(5)?.select() }
                .setNegativeButton(getString(R.string.cancel), null)
                .show()
            return
        }

        val layout = vstack {
            addEditText(getString(R.string.student_name_hint))
        }
        val etName = layout.getChildAt(0) as EditText

        layout.addView(TextView(this).apply { text = getString(R.string.parent_label); setPadding(0, 24, 0, 4) })
        val parentSpinner = Spinner(this).apply {
            adapter = ArrayAdapter(this@SuperAdminActivity,
                android.R.layout.simple_spinner_item, parents.map { it.name })
                .also { it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
        }
        layout.addView(parentSpinner)
        val etNfc = layout.addEditText(getString(R.string.nfc_optional_hint)) as EditText

        AlertDialog.Builder(this)
            .setTitle(getString(R.string.add_student))
            .setMessage(getString(R.string.set_home_hint))
            .setView(layout)
            .setPositiveButton(getString(R.string.add)) { _, _ ->
                val name = etName.text.toString().trim()
                val parentId = parents.getOrNull(parentSpinner.selectedItemPosition)?.id ?: return@setPositiveButton
                val nfc = etNfc.text.toString().trim()
                if (name.isNotEmpty()) {
                    doAction { repo.addStudent(com.busgps.android.model.AddStudentRequest(name = name, parentId = parentId, nfcId = nfc)) }
                }
            }
            .setNegativeButton(getString(R.string.cancel), null)
            .show()
    }

    private fun showAddBusDialog() {
        val layout = vstack {
            addEditText(getString(R.string.plate_hint))
        }
        val etPlate = layout.getChildAt(0) as EditText

        val schoolSpinner = Spinner(this).apply {
            adapter = ArrayAdapter(this@SuperAdminActivity,
                android.R.layout.simple_spinner_item, schools.map { it.name })
                .also { it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
        }
        layout.addView(schoolSpinner)

        AlertDialog.Builder(this)
            .setTitle(getString(R.string.add_bus))
            .setView(layout)
            .setPositiveButton(getString(R.string.add)) { _, _ ->
                val plate = etPlate.text.toString().trim()
                val schoolId = schools.getOrNull(schoolSpinner.selectedItemPosition)?.id ?: return@setPositiveButton
                if (plate.isNotEmpty()) {
                    doAction { repo.addBus(plate, schoolId) }
                }
            }
            .setNegativeButton(getString(R.string.cancel), null)
            .show()
    }

    private fun showCreateDriverDialog() {
        if (schools.isEmpty()) { toast(getString(R.string.create_school_first)); return }
        val layout = vstack {
            addEditText(getString(R.string.username))
            addEditTextPassword(getString(R.string.password))
        }
        val etUser = layout.getChildAt(0) as EditText
        val etPass = layout.getChildAt(1) as EditText
        val schoolSpinner = Spinner(this).apply {
            adapter = ArrayAdapter(this@SuperAdminActivity,
                android.R.layout.simple_spinner_item, schools.map { it.name })
                .also { it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
        }
        layout.addView(schoolSpinner)

        AlertDialog.Builder(this)
            .setTitle(getString(R.string.create_driver))
            .setView(layout)
            .setPositiveButton(getString(R.string.create)) { _, _ ->
                val u = etUser.text.toString().trim()
                val p = etPass.text.toString().trim()
                val schoolId = schools.getOrNull(schoolSpinner.selectedItemPosition)?.id
                if (u.isNotEmpty() && p.isNotEmpty()) {
                    doAction { repo.createDriver(u, p, schoolId) }
                }
            }
            .setNegativeButton(getString(R.string.cancel), null)
            .show()
    }

    private fun showCreateParentDialog() {
        if (schools.isEmpty()) { toast(getString(R.string.create_school_first)); return }
        val layout = vstack {
            addEditText(getString(R.string.full_name_hint))
            addEditText(getString(R.string.username))
            addEditTextPassword(getString(R.string.password))
        }
        val etName = layout.getChildAt(0) as EditText
        val etUser = layout.getChildAt(1) as EditText
        val etPass = layout.getChildAt(2) as EditText
        val schoolSpinner = Spinner(this).apply {
            adapter = ArrayAdapter(this@SuperAdminActivity,
                android.R.layout.simple_spinner_item, schools.map { it.name })
                .also { it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
        }
        layout.addView(schoolSpinner)

        AlertDialog.Builder(this)
            .setTitle(getString(R.string.create_parent))
            .setView(layout)
            .setPositiveButton(getString(R.string.create)) { _, _ ->
                val n = etName.text.toString().trim()
                val u = etUser.text.toString().trim()
                val p = etPass.text.toString().trim()
                val schoolId = schools.getOrNull(schoolSpinner.selectedItemPosition)?.id
                if (n.isNotEmpty() && u.isNotEmpty() && p.isNotEmpty()) {
                    doAction { repo.createParent(n, u, p, schoolId) }
                }
            }
            .setNegativeButton(getString(R.string.cancel), null)
            .show()
    }

    private fun showAssignBusDialog(studentId: String) {
        if (buses.isEmpty()) { toast(getString(R.string.no_buses_available)); return }
        AlertDialog.Builder(this)
            .setTitle(getString(R.string.assign_to_bus))
            .setItems(buses.map { it.plate }.toTypedArray()) { _, i ->
                doAction { repo.assignBus(studentId, buses[i].id) }
            }
            .show()
    }

    private fun showAssignDriverDialog(busId: String) {
        if (drivers.isEmpty()) { toast(getString(R.string.no_drivers_available)); return }
        AlertDialog.Builder(this)
            .setTitle(getString(R.string.assign_driver))
            .setItems(drivers.map { it.name }.toTypedArray()) { _, i ->
                doAction { repo.assignDriver(drivers[i].id, busId) }
            }
            .show()
    }

    private fun showEditParentCredsDialog(parent: Parent) {
        val layout = vstack {
            addEditText(getString(R.string.new_username_hint)).also { (it as EditText).setText(parent.name) }
            addEditTextPassword(getString(R.string.new_password_hint))
        }
        val etUser = layout.getChildAt(0) as EditText
        val etPass = layout.getChildAt(1) as EditText

        AlertDialog.Builder(this)
            .setTitle("Edit Login — ${parent.name}")
            .setView(layout)
            .setPositiveButton(getString(R.string.save)) { _, _ ->
                val u = etUser.text.toString().trim()
                val p = etPass.text.toString().trim()
                if (u.isNotEmpty() && p.isNotEmpty()) {
                    doAction { repo.updateParentCreds(parent.id, u, p) }
                }
            }
            .setNegativeButton(getString(R.string.cancel), null)
            .show()
    }

    // --- Helpers ---

    private fun doAction(block: suspend () -> Boolean) {
        lifecycleScope.launch {
            val ok = try { block() } catch (_: Exception) { false }
            toast(getString(if (ok) R.string.action_done else R.string.action_failed))
            if (ok) loadAll()
        }
    }

    private fun confirm(message: String, onConfirm: () -> Unit) {
        AlertDialog.Builder(this)
            .setMessage(message)
            .setPositiveButton(getString(R.string.yes)) { _, _ -> onConfirm() }
            .setNegativeButton(getString(R.string.cancel), null)
            .show()
    }

    private fun toast(msg: String) =
        Snackbar.make(binding.root, msg, Snackbar.LENGTH_SHORT).show()

    private fun vstack(block: LinearLayout.() -> Unit): LinearLayout =
        LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 16, 48, 0)
            block()
        }

    private fun LinearLayout.addEditText(hint: String): View {
        val et = EditText(context).apply { this.hint = hint }
        addView(et)
        return et
    }

    private fun LinearLayout.addEditTextPassword(hint: String): View {
        val et = EditText(context).apply {
            this.hint = hint
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        }
        addView(et)
        return et
    }

    private fun logout() {
        getSharedPreferences("session", MODE_PRIVATE).edit().clear().apply()
        ApiClient.clearSession()
        startActivity(Intent(this, RoleSelectActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        })
    }
}
