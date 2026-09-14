package io.bibuti.maivoiceandroid

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import io.bibuti.maivoiceandroid.ui.SettingsScreen
import io.bibuti.maivoiceandroid.ui.VoiceScreen
import io.bibuti.maivoiceandroid.ui.theme.MaivoiceandroidTheme
import io.bibuti.maivoiceandroid.voice.VoiceAgentViewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MaivoiceandroidTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    MaiVoiceApp()
                }
            }
        }
    }
}

@Composable
private fun MaiVoiceApp(viewModel: VoiceAgentViewModel = viewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var showSettings by rememberSaveable { mutableStateOf(false) }

    val context = LocalContext.current
    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (granted) viewModel.connect() else viewModel.permissionDenied()
    }

    if (showSettings) {
        SettingsScreen(
            currentUrl = state.serverUrl,
            speakerEnabled = state.speakerEnabled,
            onSave = {
                viewModel.saveServerUrl(it)
                showSettings = false
            },
            onToggleSpeaker = viewModel::toggleSpeaker,
            onBack = { showSettings = false },
        )
    } else {
        VoiceScreen(
            state = state,
            onConnect = {
                val granted = ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.RECORD_AUDIO,
                ) == PackageManager.PERMISSION_GRANTED
                if (granted) viewModel.connect() else permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
            },
            onDisconnect = viewModel::disconnect,
            onToggleMic = viewModel::toggleMic,
            onOpenSettings = { showSettings = true },
            onDismissError = viewModel::dismissError,
        )
    }
}
