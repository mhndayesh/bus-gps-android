package com.busgps.android.network

import com.busgps.android.model.*
import retrofit2.Response
import retrofit2.http.*

interface ApiService {

    @GET("/api/csrf-token")
    suspend fun getCsrfToken(): Response<CsrfResponse>

    @GET("/api/me")
    suspend fun getMe(): Response<MeResponse>

    // Auth — form-encoded
    @FormUrlEncoded
    @POST("/login")
    suspend fun adminLogin(
        @Field("username") username: String,
        @Field("password") password: String,
        @Field("csrf_token") csrfToken: String
    ): Response<Void>

    @FormUrlEncoded
    @POST("/driver/login")
    suspend fun driverLogin(
        @Field("username") username: String,
        @Field("password") password: String,
        @Field("csrf_token") csrfToken: String
    ): Response<Void>

    @FormUrlEncoded
    @POST("/parent/login")
    suspend fun parentLogin(
        @Field("username") username: String,
        @Field("password") password: String,
        @Field("csrf_token") csrfToken: String
    ): Response<Void>

    @GET("/logout")
    suspend fun logout(): Response<Void>

    // Parent
    @GET("/api/get_my_kids")
    suspend fun getMyKids(): Response<List<Kid>>

    // Driver
    @GET("/api/driver/manifest")
    suspend fun getManifest(): Response<List<ManifestItem>>

    @GET("/api/optimize_route/{busId}")
    suspend fun optimizeRoute(
        @Path("busId") busId: Int,
        @Query("lat") lat: Double?,
        @Query("lng") lng: Double?
    ): Response<OptimizeRouteResponse>

    // Admin — students
    @GET("/api/get_students")
    suspend fun getStudents(): Response<List<Student>>

    @POST("/api/add_student")
    suspend fun addStudent(@Body body: AddStudentRequest): Response<GenericResponse>

    @POST("/api/delete_student")
    suspend fun deleteStudent(@Body body: DeleteRequest): Response<Void>

    // Admin — parents
    @GET("/api/get_parents")
    suspend fun getParents(): Response<List<Parent>>

    @POST("/api/create_parent")
    suspend fun createParent(@Body body: CreateParentRequest): Response<GenericResponse>

    // Admin — buses
    @GET("/api/get_buses")
    suspend fun getBuses(): Response<List<Bus>>

    @POST("/api/assign_bus")
    suspend fun assignBus(@Body body: AssignBusRequest): Response<Void>

    // Admin — drivers
    @GET("/api/get_drivers")
    suspend fun getDrivers(): Response<List<Driver>>

    @POST("/api/create_driver")
    suspend fun createDriver(@Body body: CreateDriverRequest): Response<GenericResponse>

    @POST("/api/assign_driver")
    suspend fun assignDriver(@Body body: AssignDriverRequest): Response<Void>

    // Admin — stats
    @GET("/api/dashboard/stats")
    suspend fun getDashboardStats(): Response<DashboardStats>

    // Super admin
    @GET("/api/get_schools")
    suspend fun getSchools(): Response<List<School>>

    @POST("/api/add_bus")
    suspend fun addBus(@Body body: AddBusRequest): Response<GenericResponse>

    @POST("/api/delete_bus")
    suspend fun deleteBus(@Body body: DeleteBusRequest): Response<Void>

    @POST("/api/create_school_admin")
    suspend fun createSchoolAdmin(@Body body: CreateSchoolAdminRequest): Response<GenericResponse>

    @POST("/api/update_parent_credentials")
    suspend fun updateParentCreds(@Body body: UpdateParentCredsRequest): Response<Void>
}
