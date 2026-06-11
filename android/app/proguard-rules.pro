-keepattributes Signature
-keepattributes *Annotation*
-keep class com.busgps.android.model.** { *; }
-keep class retrofit2.** { *; }
-keep interface retrofit2.** { *; }
-keepclasseswithmembers class * {
    @retrofit2.http.* <methods>;
}
-keep class okhttp3.** { *; }
-keep class io.socket.** { *; }
-keep class org.osmdroid.** { *; }
-dontwarn okhttp3.**
-dontwarn okio.**
-dontwarn javax.annotation.**
