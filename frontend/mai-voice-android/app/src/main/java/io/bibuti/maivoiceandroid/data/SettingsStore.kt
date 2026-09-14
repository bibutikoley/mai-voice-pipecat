package io.bibuti.maivoiceandroid.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.settingsDataStore by preferencesDataStore(name = "mai_voice_settings")

class SettingsStore(private val context: Context) {

    val serverUrl: Flow<String> = context.settingsDataStore.data.map { prefs ->
        prefs[SERVER_URL_KEY] ?: DEFAULT_SERVER_URL
    }

    suspend fun setServerUrl(url: String) {
        context.settingsDataStore.edit { prefs -> prefs[SERVER_URL_KEY] = url }
    }

    companion object {
        const val DEFAULT_SERVER_URL = "http://10.0.2.2:7860"
        private val SERVER_URL_KEY = stringPreferencesKey("server_url")
    }
}
