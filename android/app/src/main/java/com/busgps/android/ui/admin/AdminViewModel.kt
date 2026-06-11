package com.busgps.android.ui.admin

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.busgps.android.model.*
import com.busgps.android.repository.DataRepository
import kotlinx.coroutines.launch

class AdminViewModel : ViewModel() {

    private val repo = DataRepository()

    private val _students = MutableLiveData<List<Student>>()
    val students: LiveData<List<Student>> = _students

    private val _buses = MutableLiveData<List<Bus>>()
    val buses: LiveData<List<Bus>> = _buses

    private val _drivers = MutableLiveData<List<Driver>>()
    val drivers: LiveData<List<Driver>> = _drivers

    private val _parents = MutableLiveData<List<Parent>>()
    val parents: LiveData<List<Parent>> = _parents

    private val _stats = MutableLiveData<DashboardStats>()
    val stats: LiveData<DashboardStats> = _stats

    private val _loading = MutableLiveData(false)
    val loading: LiveData<Boolean> = _loading

    private val _toast = MutableLiveData<String>()
    val toast: LiveData<String> = _toast

    fun loadAll() {
        _loading.value = true
        viewModelScope.launch {
            try {
                _students.value = repo.getStudents()
                _buses.value = repo.getBuses()
                _drivers.value = repo.getDrivers()
                _parents.value = repo.getParents()
                _stats.value = repo.getDashboardStats()
            } finally {
                _loading.value = false
            }
        }
    }

    fun addStudent(name: String, parentId: String) {
        viewModelScope.launch {
            val ok = repo.addStudent(AddStudentRequest(name = name, parentId = parentId))
            _toast.value = if (ok) "Student added" else "Failed to add student"
            if (ok) _students.value = repo.getStudents()
        }
    }

    fun deleteStudent(studentId: String) {
        viewModelScope.launch {
            val ok = repo.deleteStudent(studentId)
            _toast.value = if (ok) "Student deleted" else "Failed to delete"
            if (ok) _students.value = repo.getStudents()
        }
    }

    fun createParent(name: String, username: String, password: String) {
        viewModelScope.launch {
            val ok = repo.createParent(CreateParentRequest(name, username, password))
            _toast.value = if (ok) "Parent created" else "Failed to create parent"
            if (ok) _parents.value = repo.getParents()
        }
    }

    fun createDriver(username: String, password: String) {
        viewModelScope.launch {
            val ok = repo.createDriver(CreateDriverRequest(username, password))
            _toast.value = if (ok) "Driver created" else "Failed to create driver"
            if (ok) _drivers.value = repo.getDrivers()
        }
    }

    fun assignBus(studentId: String, busId: String) {
        viewModelScope.launch {
            val ok = repo.assignBus(studentId, busId)
            _toast.value = if (ok) "Bus assigned" else "Failed to assign bus"
        }
    }

    fun assignDriver(driverId: String, busId: String) {
        viewModelScope.launch {
            val ok = repo.assignDriver(driverId, busId)
            _toast.value = if (ok) "Driver assigned" else "Failed to assign driver"
        }
    }
}
