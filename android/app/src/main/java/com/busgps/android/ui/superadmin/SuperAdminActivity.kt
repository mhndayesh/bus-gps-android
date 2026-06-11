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
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
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
    }

    private fun setupTabs() {
        listOf("Overview", "Schools", "Students", "Buses", "Drivers", "Parents").forEach {
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
                confirm("Delete student?") {
                    doAction { repo.deleteStudent(id) }
                }
            },
            onAssignBus = { id -> showAssignBusDialog(id) }
        )
    }

    private fun showBuses() {
        binding.rvItems.adapter = SuperBusAdapter(
            buses,
            onAssignDriver = { busId -> showAssignDriverDialog(busId) },
            onDelete = { busId ->
                val plate = buses.find { it.id == busId }?.plate ?: busId
                confirm("Delete bus $plate?") {
                    doAction { repo.deleteBus(busId) }
                }
            }
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
            addEditText("School Name")
            addEditText("Admin Username")
            addEditTextPassword("Admin Password")
        }
        val schoolName = layout.getChildAt(0) as EditText
        val username = layout.getChildAt(1) as EditText
        val password = layout.getChildAt(2) as EditText

        AlertDialog.Builder(this)
            .setTitle("Create School + Admin")
            .setView(layout)
            .setPositiveButton("Create") { _, _ ->
                val sn = schoolName.text.toString().trim()
                val u = username.text.toString().trim()
                val p = password.text.toString().trim()
                if (sn.isNotEmpty() && u.isNotEmpty() && p.isNotEmpty()) {
                    doAction { repo.createSchoolAdmin(sn, u, p) }
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showAddStudentDialog() {
        val layout = vstack {
            addEditText("Student Name")
        }
        val etName = layout.getChildAt(0) as EditText

        val parentSpinner = Spinner(this).apply {
            adapter = ArrayAdapter(this@SuperAdminActivity,
                android.R.layout.simple_spinner_item, parents.map { it.name })
                .also { it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
        }
        layout.addView(parentSpinner)

        AlertDialog.Builder(this)
            .setTitle("Add Student")
            .setView(layout)
            .setPositiveButton("Add") { _, _ ->
                val name = etName.text.toString().trim()
                val parentId = parents.getOrNull(parentSpinner.selectedItemPosition)?.id ?: return@setPositiveButton
                if (name.isNotEmpty()) {
                    doAction { repo.addStudent(com.busgps.android.model.AddStudentRequest(name = name, parentId = parentId)) }
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showAddBusDialog() {
        val layout = vstack {
            addEditText("Plate Number (e.g. ABC-123)")
        }
        val etPlate = layout.getChildAt(0) as EditText

        val schoolSpinner = Spinner(this).apply {
            adapter = ArrayAdapter(this@SuperAdminActivity,
                android.R.layout.simple_spinner_item, schools.map { it.name })
                .also { it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
        }
        layout.addView(schoolSpinner)

        AlertDialog.Builder(this)
            .setTitle("Add Bus")
            .setView(layout)
            .setPositiveButton("Add") { _, _ ->
                val plate = etPlate.text.toString().trim()
                val schoolId = schools.getOrNull(schoolSpinner.selectedItemPosition)?.id ?: return@setPositiveButton
                if (plate.isNotEmpty()) {
                    doAction { repo.addBus(plate, schoolId) }
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showCreateDriverDialog() {
        val layout = vstack {
            addEditText("Username")
            addEditTextPassword("Password")
        }
        val etUser = layout.getChildAt(0) as EditText
        val etPass = layout.getChildAt(1) as EditText

        AlertDialog.Builder(this)
            .setTitle("Create Driver")
            .setView(layout)
            .setPositiveButton("Create") { _, _ ->
                val u = etUser.text.toString().trim()
                val p = etPass.text.toString().trim()
                if (u.isNotEmpty() && p.isNotEmpty()) {
                    doAction { repo.createDriver(com.busgps.android.model.CreateDriverRequest(u, p)) }
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showCreateParentDialog() {
        val layout = vstack {
            addEditText("Full Name")
            addEditText("Username")
            addEditTextPassword("Password")
        }
        val etName = layout.getChildAt(0) as EditText
        val etUser = layout.getChildAt(1) as EditText
        val etPass = layout.getChildAt(2) as EditText

        AlertDialog.Builder(this)
            .setTitle("Create Parent")
            .setView(layout)
            .setPositiveButton("Create") { _, _ ->
                val n = etName.text.toString().trim()
                val u = etUser.text.toString().trim()
                val p = etPass.text.toString().trim()
                if (n.isNotEmpty() && u.isNotEmpty() && p.isNotEmpty()) {
                    doAction { repo.createParent(com.busgps.android.model.CreateParentRequest(n, u, p)) }
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showAssignBusDialog(studentId: String) {
        if (buses.isEmpty()) { toast("No buses available"); return }
        AlertDialog.Builder(this)
            .setTitle("Assign to Bus")
            .setItems(buses.map { it.plate }.toTypedArray()) { _, i ->
                doAction { repo.assignBus(studentId, buses[i].id) }
            }
            .show()
    }

    private fun showAssignDriverDialog(busId: String) {
        if (drivers.isEmpty()) { toast("No drivers available"); return }
        AlertDialog.Builder(this)
            .setTitle("Assign Driver")
            .setItems(drivers.map { it.name }.toTypedArray()) { _, i ->
                doAction { repo.assignDriver(drivers[i].id, busId) }
            }
            .show()
    }

    private fun showEditParentCredsDialog(parent: Parent) {
        val layout = vstack {
            addEditText("New Username").also { (it as EditText).setText(parent.name) }
            addEditTextPassword("New Password")
        }
        val etUser = layout.getChildAt(0) as EditText
        val etPass = layout.getChildAt(1) as EditText

        AlertDialog.Builder(this)
            .setTitle("Edit Login — ${parent.name}")
            .setView(layout)
            .setPositiveButton("Save") { _, _ ->
                val u = etUser.text.toString().trim()
                val p = etPass.text.toString().trim()
                if (u.isNotEmpty() && p.isNotEmpty()) {
                    doAction { repo.updateParentCreds(parent.id, u, p) }
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    // --- Helpers ---

    private fun doAction(block: suspend () -> Boolean) {
        lifecycleScope.launch {
            val ok = try { block() } catch (_: Exception) { false }
            toast(if (ok) "Done" else "Failed — check connection")
            if (ok) loadAll()
        }
    }

    private fun confirm(message: String, onConfirm: () -> Unit) {
        AlertDialog.Builder(this)
            .setMessage(message)
            .setPositiveButton("Yes") { _, _ -> onConfirm() }
            .setNegativeButton("Cancel", null)
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
