package io.bibuti.maivoiceandroid.voice

enum class ConnectionStatus { Idle, Connecting, Connected, Disconnecting, Error }

enum class TranscriptRole { User, Bot }

data class TranscriptEntry(
    val id: Long,
    val role: TranscriptRole,
    val text: String,
)

data class VoiceUiState(
    val status: ConnectionStatus = ConnectionStatus.Idle,
    val serverUrl: String = "",
    val botReady: Boolean = false,
    val micEnabled: Boolean = true,
    val userSpeaking: Boolean = false,
    val botSpeaking: Boolean = false,
    val userAudioLevel: Float = 0f,
    val botAudioLevel: Float = 0f,
    val liveBotText: String = "",
    val transcripts: List<TranscriptEntry> = emptyList(),
    val error: String? = null,
)
