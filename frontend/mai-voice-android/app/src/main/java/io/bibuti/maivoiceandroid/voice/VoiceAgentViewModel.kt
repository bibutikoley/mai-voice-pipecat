package io.bibuti.maivoiceandroid.voice

import android.app.Application
import ai.pipecat.client.PipecatClientOptions
import ai.pipecat.client.PipecatEventCallbacks
import ai.pipecat.client.small_webrtc_transport.PipecatClientSmallWebRTC
import ai.pipecat.client.small_webrtc_transport.SmallWebRTCTransport
import ai.pipecat.client.transport.MsgServerToClient
import ai.pipecat.client.types.APIRequest
import ai.pipecat.client.types.BotReadyData
import ai.pipecat.client.types.Participant
import ai.pipecat.client.types.Transcript
import ai.pipecat.client.types.Value
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import io.bibuti.maivoiceandroid.data.SettingsStore
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.concurrent.atomic.AtomicLong

class VoiceAgentViewModel(application: Application) : AndroidViewModel(application) {

    private val settings = SettingsStore(application)
    private val _state = MutableStateFlow(VoiceUiState())
    val state: StateFlow<VoiceUiState> = _state.asStateFlow()

    private var client: PipecatClientSmallWebRTC? = null
    private val nextTranscriptId = AtomicLong(0)

    init {
        viewModelScope.launch {
            settings.serverUrl.collect { url -> _state.update { it.copy(serverUrl = url) } }
        }
    }

    fun saveServerUrl(url: String) {
        val value = url.trim().ifEmpty { SettingsStore.DEFAULT_SERVER_URL }
        viewModelScope.launch { settings.setServerUrl(value) }
    }

    fun permissionDenied() {
        _state.update {
            it.copy(
                status = ConnectionStatus.Error,
                error = "Microphone permission is required to talk to the bot.",
            )
        }
    }

    fun connect() {
        if (client != null || _state.value.status == ConnectionStatus.Connecting) return

        val base = _state.value.serverUrl.trim().trimEnd('/')
        _state.update {
            it.copy(
                status = ConnectionStatus.Connecting,
                error = null,
                transcripts = emptyList(),
                liveBotText = "",
                micEnabled = true,
            )
        }

        val options = PipecatClientOptions(callbacks = callbacks, enableMic = true, enableCam = false)
        val newClient = PipecatClientSmallWebRTC(SmallWebRTCTransport(getApplication()), options)
        client = newClient

        newClient.startBotAndConnect(
            APIRequest(
                endpoint = "$base/start",
                requestData = Value.Object("transport" to Value.Str("webrtc")),
            )
        ).withCallback { result ->
            result.errorOrNull?.let { error -> fail(error.toString()) }
        }
    }

    fun disconnect() {
        val current = client ?: return
        _state.update { it.copy(status = ConnectionStatus.Disconnecting) }
        current.disconnect().withCallback { releaseClient() }
    }

    fun toggleMic() {
        val current = client ?: return
        val enabled = !_state.value.micEnabled
        current.enableMic(enabled)
        _state.update { it.copy(micEnabled = enabled) }
    }

    fun dismissError() {
        _state.update {
            it.copy(
                error = null,
                status = if (it.status == ConnectionStatus.Error) ConnectionStatus.Idle else it.status,
            )
        }
    }

    override fun onCleared() {
        client?.release()
        client = null
        super.onCleared()
    }

    private fun fail(message: String) {
        _state.update { it.copy(status = ConnectionStatus.Error, error = message) }
        releaseClient(keepError = true)
    }

    private fun releaseClient(keepError: Boolean = false) {
        client?.release()
        client = null
        _state.update {
            it.copy(
                status = ConnectionStatus.Idle,
                error = if (keepError) it.error else null,
                botReady = false,
                userSpeaking = false,
                botSpeaking = false,
                userAudioLevel = 0f,
                botAudioLevel = 0f,
                liveBotText = "",
            )
        }
    }

    private fun appendTranscript(role: TranscriptRole, text: String) {
        if (text.isBlank()) return
        _state.update {
            it.copy(
                transcripts = it.transcripts +
                    TranscriptEntry(nextTranscriptId.incrementAndGet(), role, text.trim())
            )
        }
    }

    private val callbacks = object : PipecatEventCallbacks() {

        override fun onBackendError(message: String) = fail(message)

        override fun onConnected() {
            _state.update { it.copy(status = ConnectionStatus.Connected) }
        }

        override fun onDisconnected() {
            releaseClient()
        }

        override fun onBotReady(data: BotReadyData) {
            _state.update { it.copy(botReady = true) }
        }

        override fun onUserStartedSpeaking() {
            _state.update { it.copy(userSpeaking = true) }
        }

        override fun onUserStoppedSpeaking() {
            _state.update { it.copy(userSpeaking = false, userAudioLevel = 0f) }
        }

        override fun onBotStartedSpeaking() {
            _state.update { it.copy(botSpeaking = true) }
        }

        override fun onBotStoppedSpeaking() {
            _state.update { current ->
                val text = current.liveBotText.trim()
                current.copy(
                    botSpeaking = false,
                    botAudioLevel = 0f,
                    liveBotText = "",
                    transcripts = if (text.isBlank()) current.transcripts
                    else current.transcripts + TranscriptEntry(
                        nextTranscriptId.incrementAndGet(),
                        TranscriptRole.Bot,
                        text,
                    ),
                )
            }
        }

        override fun onUserAudioLevel(level: Float) {
            _state.update { it.copy(userAudioLevel = level) }
        }

        override fun onRemoteAudioLevel(level: Float, participant: Participant) {
            _state.update { it.copy(botAudioLevel = level) }
        }

        override fun onUserTranscript(data: Transcript) {
            if (data.final) appendTranscript(TranscriptRole.User, data.text)
        }

        override fun onBotLLMText(data: MsgServerToClient.Data.BotLLMTextData) {
            _state.update { it.copy(liveBotText = it.liveBotText + data.text) }
        }
    }
}
