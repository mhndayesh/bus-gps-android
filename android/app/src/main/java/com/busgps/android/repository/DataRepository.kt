package com.busgps.android.repository

import com.busgps.android.model.*
import com.busgps.android.network.ApiClient

class DataRepository {

    // Parent
    suspend fun getMyKids(): List<Kid> =
        ApiClient.api.getMyKids().body() ?: emptyList()

    // Driver
    suspend fun getManifest(): List<ManifestItem> =
        ApiClient.api.getManifest().body() ?: emptyList()

    suspend fun optimizeRoute(busId: Int, lat: Double?, lng: Double?): List<RouteStop> =
        ApiClient.api.optimizeRoute(busId, lat, lng).body()?.stops ?: emptyList()

    // Admin
    suspend fun getStudents(): List<Student> =
        ApiClient.api.getStudents().body() ?: emptyList()

    suspend fun addStudent(req: AddStudentRequest): Boolean =
        ApiClient.api.addStudent(req).isSuccessful

    suspend fun deleteStudent(studentId: String): Boolean =
        ApiClient.api.deleteStudent(DeleteRequest(studentId = studentId)).isSuccessful

    suspend fun updateStudentLocation(studentId: String, lat: Double, lng: Double, address: String): Boolean =
        ApiClient.api.updateStudentLocation(
            UpdateStudentLocationRequest(studentId, lat, lng, address)
        ).isSuccessful

    suspend fun getParents(): List<Parent> =
        ApiClient.api.getParents().body() ?: emptyList()

    suspend fun createParent(req: CreateParentRequest): Boolean =
        ApiClient.api.createParent(req).isSuccessful

    suspend fun createParent(name: String, username: String, password: String, schoolId: Int?): Boolean =
        ApiClient.api.createParent(CreateParentRequest(name, username, password, schoolId)).isSuccessful

    suspend fun getBuses(): List<Bus> =
        ApiClient.api.getBuses().body() ?: emptyList()

    suspend fun assignBus(studentId: String, busId: String): Boolean =
        ApiClient.api.assignBus(AssignBusRequest(studentId, busId)).isSuccessful

    suspend fun getDrivers(): List<Driver> =
        ApiClient.api.getDrivers().body() ?: emptyList()

    suspend fun createDriver(req: CreateDriverRequest): Boolean =
        ApiClient.api.createDriver(req).isSuccessful

    suspend fun createDriver(username: String, password: String, schoolId: Int?): Boolean =
        ApiClient.api.createDriver(CreateDriverRequest(username, password, schoolId)).isSuccessful

    suspend fun assignDriver(driverId: String, busId: String): Boolean =
        ApiClient.api.assignDriver(AssignDriverRequest(driverId, busId)).isSuccessful

    suspend fun getDashboardStats(): DashboardStats? =
        ApiClient.api.getDashboardStats().body()

    // Super admin
    suspend fun getSchools(): List<School> =
        ApiClient.api.getSchools().body() ?: emptyList()

    suspend fun addBus(plate: String, schoolId: Int): Boolean =
        ApiClient.api.addBus(AddBusRequest(plate, schoolId)).isSuccessful

    suspend fun deleteBus(busId: String): Boolean =
        ApiClient.api.deleteBus(DeleteBusRequest(busId)).isSuccessful

    suspend fun createSchoolAdmin(schoolName: String, username: String, password: String): Boolean =
        ApiClient.api.createSchoolAdmin(CreateSchoolAdminRequest(schoolName, username, password)).isSuccessful

    suspend fun updateParentCreds(parentId: String, username: String, password: String): Boolean =
        ApiClient.api.updateParentCreds(UpdateParentCredsRequest(parentId, username, password)).isSuccessful
}
