# ── Retrofit ──────────────────────────────────────────────────────────────────
-dontwarn retrofit2.**
-keep class retrofit2.** { *; }
-keepattributes Signature
-keepattributes Exceptions
-keepattributes *Annotation*

# ── OkHttp / Okio ─────────────────────────────────────────────────────────────
-dontwarn okhttp3.**
-dontwarn okio.**
-keep class okhttp3.** { *; }
-keep interface okhttp3.** { *; }

# ── Gson ──────────────────────────────────────────────────────────────────────
-dontwarn sun.misc.**
-keep class com.google.gson.** { *; }
-keep class * implements com.google.gson.TypeAdapterFactory
-keep class * implements com.google.gson.JsonSerializer
-keep class * implements com.google.gson.JsonDeserializer
# Preserve fields annotated with @SerializedName so Gson can map JSON keys
-keepclassmembers,allowobfuscation class * {
    @com.google.gson.annotations.SerializedName <fields>;
}

# ── App models & API interfaces ───────────────────────────────────────────────
# Keep all data classes used in Retrofit/Gson serialisation
-keep class com.redditcommentcleaner.model.** { *; }
-keep class com.redditcommentcleaner.api.** { *; }

# ── Kotlin ────────────────────────────────────────────────────────────────────
-keep class kotlin.** { *; }
-keep class kotlin.Metadata { *; }
-dontwarn kotlin.**
-keepclassmembers class **$WhenMappings {
    <fields>;
}
-keepclassmembers class kotlin.coroutines.** { *; }

# ── AndroidX Security / EncryptedSharedPreferences ───────────────────────────
-keep class androidx.security.crypto.** { *; }

# ── BuildConfig ───────────────────────────────────────────────────────────────
-keep class com.redditcommentcleaner.BuildConfig { *; }
