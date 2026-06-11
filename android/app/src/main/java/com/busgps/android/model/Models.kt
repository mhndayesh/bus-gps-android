package com.busgps.android.model

import com.google.gson.annotations.SerializedName

data class CsrfResponse(
    @SerializedName("token") val csrfToken: String
)

data class MeResponse(
    val role: String?,
    val name: String?
)

data class Kid(
    val id: String,
    val name: String,
    val code: String?,
    @SerializedName("on_bus") val onBus: Boolean,
    @SerializedName("bus_id") val busId: Int?,
    @SerializedName("bus_plate") val busPlate: String?
)

data class Student(
    val id: String,
    val name: String,
    val code: String?,
    @SerializedName("parent_id") val parentId: String?,
    val lat: Double?,
    val lng: Double?,
    @SerializedName("address_text") val addressText: String?
)

data class ManifestItem(
    val id: String,
    val name: String,
    val lat: Double?,
    val lng: Double?,
    val status: String?   // "BOARDED" | "DROPPED" | null
)

data class Bus(
    val id: String,
    val plate: String,
    @SerializedName("school_id") val schoolId: Int?
)

data class Driver(
    val id: String,
    val name: String,
    @SerializedName("school_id") val schoolId: Int?
)

data class Parent(
    val id: String,
    val name: String
)

data class School(
    val id: Int,
    val name: String
)

data class DashboardStats(
    @SerializedName("total_buses") val totalBuses: Int,
    @SerializedName("active_buses") val activeBuses: Int,
    @SerializedName("total_students") val totalStudents: Int,
    @SerializedName("present_students") val presentStudents: Int,
    @SerializedName("absent_students") val absentStudents: Int
)

data class RouteStop(
    val name: String,
    val lat: Double,
    val lng: Double
)

data class OptimizeRouteResponse(
    val status: String,
    val stops: List<RouteStop>,
    val count: Int
)

data class GenericResponse(
    val status: String?,
    val id: Any?,
    val message: String?
)

// Socket.IO payloads
data class BusLocationUpdate(
    @SerializedName("bus_id") val busId: Int,
    val lat: Double,
    val lng: Double,
    val speed: Double
)

data class StudentStatusUpdate(
    @SerializedName("student_id") val studentId: String,
    val status: String,
    @SerializedName("bus_id") val busId: Int,
    val timestamp: String?
)

data class AddStudentRequest(
    val name: String,
    @SerializedName("parent_id") val parentId: String,
    @SerializedName("nfc_id") val nfcId: String = "",
    val lat: Double? = null,
    val lng: Double? = null,
    @SerializedName("address_text") val addressText: String? = null
)

data class CreateParentRequest(
    val name: String,
    val username: String,
    val password: String
)

data class CreateDriverRequest(
    val username: String,
    val password: String
)

data class AssignBusRequest(
    @SerializedName("student_id") val studentId: String,
    @SerializedName("bus_id") val busId: String
)

data class AssignDriverRequest(
    @SerializedName("driver_id") val driverId: String,
    @SerializedName("bus_id") val busId: String
)

data class DeleteRequest(
    @SerializedName("student_id") val studentId: String? = null,
    @SerializedName("bus_id") val busId: Int? = null,
    @SerializedName("driver_id") val driverId: String? = null
)

data class AddBusRequest(
    val plate: String,
    @SerializedName("school_id") val schoolId: Int
)

data class DeleteBusRequest(
    @SerializedName("bus_id") val busId: String
)

data class CreateSchoolAdminRequest(
    @SerializedName("school_name") val schoolName: String,
    val username: String,
    val password: String
)

data class UpdateParentCredsRequest(
    @SerializedName("parent_id") val parentId: String,
    val username: String,
    val password: String
)

data class DriverInfo(
    @SerializedName("bus_id") val busId: Int?,
    val plate: String?
)
